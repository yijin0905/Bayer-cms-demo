#!/bin/zsh
set -euo pipefail
set +x

readonly account="openai-api"
readonly service="com.openai.api-key.bayer-cms"
readonly label="OpenAI API Key (Bayer CMS)"

print "Paste the same new OpenAI API key at both secure prompts, pressing Return after each."
print "The key will not be echoed or written to this project."

/usr/bin/security add-generic-password \
  -a "$account" \
  -s "$service" \
  -l "$label" \
  -U \
  -w

if /usr/bin/security find-generic-password \
  -a "$account" \
  -s "$service" \
  >/dev/null 2>&1; then
  print "OpenAI API key saved in macOS Keychain."
else
  print -u2 "The Keychain item could not be verified."
  exit 1
fi
