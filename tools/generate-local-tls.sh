#!/usr/bin/env bash
set -euo pipefail

out_dir="${CSP_TLS_DIR:-runtime/tls}"
hostname_value="${CSP_TLS_HOSTNAME:-srv-ai}"
primary_ip="${CSP_TLS_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"

mkdir -p "$out_dir"
umask 077

ca_key="$out_dir/ca.key"
ca_crt="$out_dir/ca.crt"
server_key="$out_dir/server.key"
server_csr="$out_dir/server.csr"
server_crt="$out_dir/server.crt"
ext_file="$out_dir/server.ext"

if [[ ! -s "$ca_key" || ! -s "$ca_crt" ]]; then
  openssl genrsa -out "$ca_key" 3072
  openssl req -x509 -new -sha256 -days 3650 \
    -key "$ca_key" -out "$ca_crt" \
    -subj '/CN=Support Endpoint Local CA/O=Support Endpoint'
fi

openssl genrsa -out "$server_key" 2048
openssl req -new -sha256 -key "$server_key" -out "$server_csr" \
  -subj "/CN=$hostname_value/O=Support Endpoint"

{
  echo 'basicConstraints=CA:FALSE'
  echo 'keyUsage=digitalSignature,keyEncipherment'
  echo 'extendedKeyUsage=serverAuth'
  echo "subjectAltName=DNS:$hostname_value${primary_ip:+,IP:$primary_ip}"
} > "$ext_file"

openssl x509 -req -sha256 -days 825 \
  -in "$server_csr" -CA "$ca_crt" -CAkey "$ca_key" -CAcreateserial \
  -out "$server_crt" -extfile "$ext_file"

rm -f "$server_csr" "$ext_file"
chmod 600 "$ca_key" "$server_key"
chmod 644 "$ca_crt" "$server_crt"

openssl verify -CAfile "$ca_crt" "$server_crt"
printf 'tls_hostname=%s\n' "$hostname_value"
printf 'tls_ip=%s\n' "${primary_ip:-none}"
printf 'ca_certificate=%s\n' "$ca_crt"
