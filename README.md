OpenStack to CloudFlare DNS Sync
================================

This script reads the server from OpenStack and creates, updates, or deletes an entry in cloudflare.

# Install dependencies
`pip install -r requirements.txt`

Make sure openstack bin is in $PATH.

## Example

```
python dnssync.py \
  --osp-username user1 \
  --osp-password user1sPassword \
  --osp-auth-url http://osp.lab.tld:5000 \
  --osp-network-name 'private_network' \
  --cf-email='cloudflare_email@examplemail.com' \
  --cf-token='<cloudflare-api-token>' \
  --cf-zone lab.tld \
  --cf-subdomain vms.lab.tld \
  --osp-project lab \
  --hostname-format name \
  --osp-network-subnet='192.168.1.0/24'
```

### Example of an execution
```
Checking if glusterfs-3.vms.takeshi.se (glusterfs-3) exists in cloudflare dns.
        Record found.
                UPDATED: glusterfs-3.vms.takeshi.se 192.168.1.122 -> 192.168.1.17

Checking if glusterfs-2.vms.takeshi.se (glusterfs-2) exists in cloudflare dns.
        Record not found.
                CREATED: glusterfs-2.vms.takeshi.se 192.168.1.20

Checking if glusterfs-1.vms.takeshi.se (glusterfs-1) exists in cloudflare dns.
        Record not found.
                CREATED: glusterfs-1.vms.takeshi.se 192.168.1.16

Checking if ocp-app-2.vms.takeshi.se (ocp-app-2) exists in cloudflare dns.
        Record found.

Checking if ocp-app-1.vms.takeshi.se (ocp-app-1) exists in cloudflare dns.
        Record found.

Checking if ocp-infra-3.vms.takeshi.se (ocp-infra-3) exists in cloudflare dns.
        Record found.

Checking if ocp-infra-2.vms.takeshi.se (ocp-infra-2) exists in cloudflare dns.
        Record found.

Checking if ocp-infra-1.vms.takeshi.se (ocp-infra-1) exists in cloudflare dns.
        Record found.

Checking if ocp-master-3.vms.takeshi.se (ocp-master-3) exists in cloudflare dns.
        Record found.

Checking if ocp-master-2.vms.takeshi.se (ocp-master-2) exists in cloudflare dns.
        Record found.

Checking if ocp-master-1.vms.takeshi.se (ocp-master-1) exists in cloudflare dns.
        Record found.

Checking if bastion.vms.takeshi.se (bastion) exists in cloudflare dns.
        Record found.
```

## Help

Run `python dnssync.py --help`

