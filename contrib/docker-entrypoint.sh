#!/usr/bin/env bash

# Removes ipv6 localhost address
# Electrumx tests break without this
# https://github.com/moby/moby/issues/35954
sed 's/^::1.*localhost/::1\tip6-localhost/g' /etc/hosts > /etc/hosts.tmp
cat /etc/hosts.tmp > /etc/hosts
rm -f /etc/hosts.tmp

gosu user "$@"
