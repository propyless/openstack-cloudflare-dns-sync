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

## Help

Run `python dnssync.py --help`

