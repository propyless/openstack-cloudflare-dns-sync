#!/usr/bin/env python

import subprocess
import os
import sys
import yaml
import CloudFlare
import argparse
from netaddr import IPNetwork, IPAddress


def fetch_osp_servers(env_var) -> dict:
  """ Fetch server list for project in OSP """
  env = {}
  env.update(os.environ)
  env.update(env_var)

  osp_output = subprocess.Popen(
    ['openstack', 'server', 'list', '-f', 'yaml'],
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
    )

  server_list, errors = osp_output.communicate()
  if errors:
    print("{}".format(errors.decode()))
    sys.exit(1)
  return yaml.load(server_list.decode())


def fetch_dns_records(cf, zone_name, domain_filter):
  """ Get a list of the DNS records in the subdomain specified """
  try:
    zones = cf.zones.get(params={'name': zone_name, 'per_page': 1})
  except CloudFlare.exceptions.CloudFlareAPIError as e:
    sys.exit('/zones.get %d %s - api call failed' % (e, e))
  except Exception as e:
    sys.exit('/zones.get - %s - api call failed' % (e))

  if len(zones) == 0:
    sys.exit('No zones found')

  zone = zones[0]
  zone_id = zone['id']

  # request the DNS records from that zone
  try:
    dns_records = cf.zones.dns_records.get(zone_id, params={'per_page': 100})
  except CloudFlare.exceptions.CloudFlareAPIError as e:
    sys.exit('/zones/dns_records.get %d %s - api call failed' % (e, e))

  osp_records = {rcd['name']: rcd for rcd in dns_records if rcd['name'].endswith(domain_filter)}
  return osp_records, zone_id


def add_dns_record(cf, zone_id, dns_record):
  """ Adds DNS record """
  dns_name = dns_record['name']
  ip_address = dns_record['content']
  try:
      dns_record = cf.zones.dns_records.post(zone_id, data=dns_record)
  except CloudFlare.exceptions.CloudFlareAPIError as e:
      sys.exit('/zones.dns_records.post %s - %d %s - api call failed' % (dns_name, e, e))
  print('\t\tCREATED: {} {}'.format(dns_name, ip_address))


def update_dns_record(cf, zone_id, dns_record_id, dns_name, old_ip, new_ip):
  """ Updates a DNS record """
  dns_record = {
    'name': dns_name,
    'content': new_ip,
    'type': 'A',
    'ttl': 120,
    'proxied': False
  }

  try:
    dns_record = cf.zones.dns_records.put(zone_id, dns_record_id, data=dns_record)
  except CloudFlare.exceptions.CloudFlareAPIError as e:
    sys.exit('/zones.dns_records.put %s - %d %s - api call failed' % (dns_name, e, e))
  print('\t\tUPDATED: {} {} -> {}'.format(dns_name, old_ip, new_ip))


def delete_dns_record(cf, zone_id, dns_record_id, dns_name):
  """ Deletes a DNS record """
  try:
    dns_record = cf.zones.dns_records.delete(zone_id, dns_record_id)
    print('DELETED: {}'.format(dns_name))
  except CloudFlare.exceptions.CloudFlareAPIError as e:
    sys.exit('/zones.dns_records.delete %s - %d %s - api call failed' % (dns_name, e, e))

def main(args):
  # 'name' or 'ip' based naming
  # IP based would allow for instances that share name
  # Name based would not allow for duplicate instance names

  # Validate the args
  if not args.cf_use_config:
    # Make sure that the cf_email, token and domain are specified if not using cloudflare config
    if args.cf_email and args.cf_token and args.cf_domain:
      pass
    else:
      print('If not using .cloudflare.cfg then Cloudflare email, token and domain must be specified.')
      sys.exit(1)

  dns_name_type = args.hostname_format

  # CloudFlare auth info
  cf_email = args.cf_email
  cf_token = args.cf_token
  cf_domain = args.cf_domain
  cf_subdomain = args.cf_subdomain

  osp_client_env_vars = {
    'OS_USERNAME': args.osp_username,
    'OS_PASSWORD': args.osp_password,
    'OS_AUTH_URL': args.osp_auth_url,
    'OS_PROJECT_NAME': args.osp_project_name,
    'OS_USER_DOMAIN_NAME': args.osp_user_domain_name,
    'OS_PROJECT_DOMAIN_NAME': args.osp_project_domain_name,
    'OS_IDENTITY_API_VERSION': args.osp_identity_api_vers,
  }

  osp_network_name = args.osp_network_name
  osp_network_subnet = args.osp_network_subnet

  cf = CloudFlare.CloudFlare(email=cf_email, token=cf_token)
  instance_records, zone_id = fetch_dns_records(cf=cf,
                                       zone_name=cf_domain,
                                       domain_filter=cf_subdomain
                                      )

  server_list = fetch_osp_servers(osp_client_env_vars)

  # A List to populate with servers that no longer exist in OSP
  server_names = []

  for server in server_list:
    # Set these vars at start
    network_name = False
    network_ip = False
    dns_name = False

    # Filter networks for the network we are interested in
    for network in server['Networks'].split('; '):
      # ignore all networks except for the one we care about.
      if osp_network_name in network:
        _network = network.split('=')
        network_name = _network[0]
        network_ips = _network[-1].split(', ')
        # So we want to track if the ip is in the specified in the network.
        network_ip = [ip for ip in network_ips if IPAddress(ip) in IPNetwork(osp_network_subnet)][0]

    # Set a DNS name based on the name type set
    if dns_name_type == 'name':
      dns_name = "{}.{}".format(server['Name'], cf_subdomain)
    elif dns_name_type == 'ip':
      if network_name and network_ip:
        dns_name = "{}.{}".format(network_ip.replace('.', '-'), cf_subdomain)

    # After building the dns_name, add it to the server_names list.
    server_names.append(dns_name)

    # Check if the DNS records for dns_name exists in CF
    print("Checking if {} ({}) exists in cloudflare dns.".format(dns_name, server['Name']))
    if dns_name in instance_records:
      print('\tRecord found.'.format(dns_name))

      # Check if A records points to correct place
      if instance_records[dns_name]['content'] != network_ip:
        update_dns_record(
          cf=cf,
          zone_id=zone_id,
          dns_record_id=instance_records[dns_name]['id'],
          dns_name=dns_name,
          old_ip=instance_records[dns_name]['content'],
          new_ip=network_ip,
        )

    elif dns_name not in instance_records:
      print('\tRecord not found.')
      dns_record = {
	'name': dns_name,
	'content': network_ip,
	'type': 'A',
	'ttl': 120,
	'proxied': False
      }
      add_dns_record(cf, zone_id, dns_record)

    print('')

  # Purge all entries that we don't have an instance for
  purge_dns_entries = [record for record in instance_records if record not in server_names]
  if purge_dns_entries and args.purge_missing:
    print("Purging non-existent domains")
    for entry in purge_dns_entries:
      delete_dns_record(cf, zone_id, instance_records[entry]['id'], entry)

def parse_args():
  parser = argparse.ArgumentParser(description="""
This is a tool for creating and updating OpenStack instances into cloudflare DNS.
""")
  # General arguments
  parser.add_argument('--hostname-format', action='store', dest='hostname_format', default='ip',
                     help='This is the format in which the hostname for the subdomain will be created. ip: 192-168-1-1.vms.local.tld. name: instancename.vms.local.tld. Default is "ip".')
  parser.add_argument('--purge-missing', action='store_true', dest='purse_missing', default=False,
                     help='Delete any DNS entries which no longer exist in OpenStack'

  # Add argument parser group for cloudflare opts
  cf_args = parser.add_argument_group('CloudFlare arguments')

  cf_args.add_argument('--cf-login-with-config', action='store_true', dest='cf_use_config', default=False,
                      help='If set cloudflare authentication will take credentials from cloudflare.cfg as described here: https://github.com/cloudflare/python-cloudflare#providing-cloudflare-username-and-api-key and ignore the --cf-email and --cf-token parameters.')
  cf_args.add_argument('--cf-email', action='store', dest='cf_email',
                      help='Email you use to log in to CloudFlare.')
  cf_args.add_argument('--cf-token', action='store', dest='cf_token',
                      help='CloudFlare API Token.')
  cf_args.add_argument('--cf-zone', action='store', dest='cf_domain',
                      help='The zone (domain) you wish to get dns records from. For example: domain.tld')
  cf_args.add_argument('--cf-subdomain', action='store', dest='cf_subdomain',
                      help='The subdomain which shall be used to create dns records for. For example setting this to: vms.domain.tld, will create instances like so: 192-168-1-1.vms.domain.tld')


  # Add argument parser group for OpenStack
  osp_args = parser.add_argument_group('OpenStack arguments')
  osp_args.add_argument('--osp-username', action='store', dest='osp_username', required=True,
                      help='OpenStack Username')
  osp_args.add_argument('--osp-password', action='store', dest='osp_password', required=True,
                      help='OpenStack Password')
  osp_args.add_argument('--osp-auth-url', action='store', dest='osp_auth_url', required=True,
                      help='OpenStack Authentication URL')
  osp_args.add_argument('--osp-project', action='store', dest='osp_project_name', required=True,
                      help='Name of the project in openstack.')
  osp_args.add_argument('--osp-user-domain-name', action='store', dest='osp_user_domain_name', default='default',
                      help='OpenStack Domain your user is a member of. Default is set to \'default\'.')
  osp_args.add_argument('--osp-project-domain-name', action='store', dest='osp_project_domain_name', default='default',
                      help='OpenStack Domain the specified project is a member of. Default is set to \'default\'.')
  osp_args.add_argument('--osp-identity_api_vers', action='store', dest='osp_identity_api_vers', default='3',
                      help='OpenStack identity api version. Default is set to \'3\'')
  osp_args.add_argument('--osp-network-name', action='store', dest='osp_network_name', required=True,
                      help='Name of the network in the project which should be used to map instance ip to hostnames in cloudflare. For example if the private network called "private_network" is used, then specify "private_network"')
  osp_args.add_argument('--osp-network-subnet', action='store', dest='osp_network_subnet', required=True,
                      help='The subnet/cidr range to add in cloudflare. Eg. 192.168.0.0/24')

  return parser.parse_args()


if __name__ == '__main__':
  args = parse_args()
  main(args)
