#!/bin/bash

# curl-dataset.sh
# This script downloads a specified dataset from OneDrive and unzips it into the datasets/
# Usage: ./curl-dataset.sh [--help|-h] [-d <dataset-name>]

mkdir -p datasets
cd datasets

if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  echo "Usage: $0 [--help|-h] [-d <dataset-name>]"
  echo ""
  echo "Options:"
  echo "  --help, -h            Show this help message and exit"
  echo "  -d <dataset-name>     Specify the dataset to download (currently not implemented)"
  exit 0
fi
if [ "$1" == "-d" ] && [ -z "$2" ]; then
  echo "Error: -d option requires a dataset name argument."
  exit 1
fi
if [ "$1" == "-d" ] && [ -n "$2" ]; then
  DATASET_NAME="$2"
  DATASETS_YAML=$(curl 'https://ueeduph-my.sharepoint.com/personal/concepcion_timothyjames_ue_edu_ph/_layouts/15/download.aspx?SourceUrl=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets%2Fdatasets%2Eyaml' \
    -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
    -H 'accept-language: en-US,en;q=0.9' \
    -H 'cookie: MSFPC=GUID=018d8352266641bfa8680659823058c3&HASH=018d&LV=202501&V=4&LU=1738235237094; rtFa=WO9c+3n+GWh27WpR1MWAc691lwh75C0QMpZdz6W4lmImNzdlMThiODctNTFkMy00OWUxLWIyODEtZGZkYTVhOTI2MDYxIzEzNDA0NjI3NTY2MDM0NDc3MyM2ZTM4Y2VhMS0zMGQ5LTUwMDAtZWVhOS1hMzJhNWQ2N2VkOGUjY29uY2VwY2lvbi50aW1vdGh5amFtZXMlNDB1ZS5lZHUucGgjMTk2MDEwI2dmYktidWJ6dXRzZ0NseGZpOV9rQ0g0TndYYyNnZmJLYnVienV0c2dDbHhmaTlfa0NINE53WGN12hbsUFZcwVe4kt9Y+KbLDkAxhxEbdXqV77f/cTgWi0mpPfzdODhX2u6rcSyQkn+SLa0yPz9Vbrr5K7utj0ExKH5JNMXftq5gIv9GXhqhmZNLjpj/ICo4hiZ6+J5TnsvjukbDVMRR8dinZscww4yVEvQFii5teYxCvjQTMLRijOXmROavqVtkS7xeWRLNGFHhfRpC1UqaVN2UFGN2OE1jkK+WWxcmNtpa1gHjyPa/Ilhc/4tbRPzmix4RDZfeuFH+yUHjb1wlk+csky0va4ZwzDwNSTFu8Gm+MoPc1xFaH9wQ9No0W1byJB9vh1Uh4y9iHQWHc5W84Mwdyb7YO+hg4AAAAA==; SIMI=eyJzdCI6MH0=; FedAuth=77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjE0LDBoLmZ8bWVtYmVyc2hpcHwxMDAzMjAwMmNmYWFmOTFlQGxpdmUuY29tLDAjLmZ8bWVtYmVyc2hpcHxjb25jZXBjaW9uLnRpbW90aHlqYW1lc0B1ZS5lZHUucGgsMTM0MDA2OTQ2MjcwMDAwMDAwLDEzMzM1NjAyNDQxMDAwMDAwMCwxMzQwNTA1OTU2NjAxODc4ODMsMTM2LjE1OC42MS4xOTgsNjcsNzdlMThiODctNTFkMy00OWUxLWIyODEtZGZkYTVhOTI2MDYxLCwwMDdiYzc5OS03YmZmLThjOWQtMTA1Zi04ODIyMTE3NWE5MGEsNmUzOGNlYTEtMzBkOS01MDAwLWVlYTktYTMyYTVkNjdlZDhlLDZlMzhjZWExLTMwZDktNTAwMC1lZWE5LWEzMmE1ZDY3ZWQ4ZSwsMCwxMzQwNDcxMzk2NjAwMzE1OTYsMTM0MDQ4ODY3NjYwMDMxNTk2LCwsZXlKNGJYTmZZMk1pT2lKYlhDSkRVREZjSWwwaUxDSjRiWE5mYzNOdElqb2lNU0lzSW5CeVpXWmxjbkpsWkY5MWMyVnlibUZ0WlNJNkltTnZibU5sY0dOcGIyNHVkR2x0YjNSb2VXcGhiV1Z6UUhWbExtVmtkUzV3YUNJc0luVjBhU0k2SW1FMVVqRjBVbXQwTjJ0eE9GOWhOMGMyTUVoVFFVRWlMQ0poZFhSb1gzUnBiV1VpT2lJeE16UXdNRFk1TkRZeU56QXdNREF3TURBaWZRPT0sMjY1MDQ2Nzc0Mzk5OTk5OTk5OSwxMzQwNDYyNzU2NTAwMDAwMDAsNjgxOGY5ZGYtM2I3Ny00NTI5LWIzMmEtZWI5OTE2M2FmYTU4LCwsLCwsMTE1MjkyMTUwNDYwNjg0Njk3NiwsMTk2MDEwLHJMSFBYbWZOcnlzVVBfZ3hrbzd1VzJoSnRaMCwsTEhodVpoU01FaGNMN0x6WkhyRDZNa2k3TG53YkgvMHllSGRFTmZ2dks5ckhkQlBDdGF6U0ZiOXgxRWJCNkhkWnlPVE4ydldjQVRNY3Fkb0NRYlJ1UWVZMDdUQUhubENzaDdObE40RGhPMWJVSGh5WEphbzNuTEhNMEhPZnhUWmZkYUVqQ1l0bmZIbTdIYzZxTlR6RUJRYS9QcEJKdnBWcHpycHNHU3VoeUZSazc5ZVdFdUlwRWpjWkRLRitJVThaRndqMkdWZEFuSDV2alY2dTJNNmY4enZ6K1FUak02MXIvV3cweVVxTTRvdEpHdDMwdlVZV1ZBSnlrUS9ZMlpZSk9OZ1RMRHg3bzE4ZXcvT2txSTRIaUUwSDY0bEJVRWcvd2wyNlRGemNIQkRxQmNzNEVqZ1U0NitqTnBEbTdVemwydWtKL3o0bTBtbFpTQmlJQzFpdWdnPT08L1NQPg==; FeatureOverrides_experiments=[]; msal.cache.encryption=%7B%22id%22%3A%220199d1b4-f122-7fbc-9428-e22afa0e1d92%22%2C%22key%22%3A%22EtQ4ugS0fVUhLlA3mw3rd8vB__NRXSrXm23fpr4ZZmI%22%7D; MicrosoftApplicationsTelemetryDeviceId=1fcfbe4b-a76f-464a-8c36-a0b2e9904a86; SPA_RT=; ai_session=u7e6fZP0ZRdoS/DI85uvyY|1760159917922|1760160416999' \
    -H 'dnt: 1' \
    -H 'if-none-match: "{C2BABEED-5EEC-479A-A8DF-318C9EB7200D},12"' \
    -H 'priority: u=0, i' \
    -H 'referer: https://ueeduph-my.sharepoint.com/my?id=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets%2Fdatasets%2Eyaml&parent=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets&ga=1' \
    -H 'sec-ch-ua: "Not?A_Brand";v="99", "Chromium";v="130"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "Windows"' \
    -H 'sec-fetch-dest: iframe' \
    -H 'sec-fetch-mode: navigate' \
    -H 'sec-fetch-site: same-origin' \
    -H 'sec-fetch-user: ?1' \
    -H 'sec-gpc: 1' \
    -H 'service-worker-navigation-preload: {"supportsFeatures":[1855,61313,62475]}' \
    -H 'upgrade-insecure-requests: 1' \
    -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')

  # Extract the curl block for the dataset
  CURL_CMD=$(echo "$DATASETS_YAML" | awk -v name="$DATASET_NAME" '
    $0 ~ "name: "name {
      in_block=1
    }
    in_block && $0 ~ "curl: *\\| *$" {
      in_curl=1
      next
    }
    in_curl && ($0 ~ "^    [a-zA-Z_-]+:" || $0 ~ "^  - name:") {
      exit
    }
    in_curl {
      sub(/^      /, "")
      print
    }
  ')

  if [ -z "$CURL_CMD" ]; then
    echo "$CURL_CMD"
    echo "Error: Dataset '$DATASET_NAME' not found or does not have a curl command."
    exit 1
  fi
  eval "$CURL_CMD"

  unzip "$DATASET_NAME"
  rm "$DATASET_NAME"

  exit 0
fi