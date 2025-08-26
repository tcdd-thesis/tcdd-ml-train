#!/bin/bash
# make datasets folder if not exists
mkdir -p datasets
cd datasets
# download traffic-signs-detection1.zip from onedrive
curl 'https://ueeduph-my.sharepoint.com/personal/concepcion_timothyjames_ue_edu_ph/_layouts/15/download.aspx?SourceUrl=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets%2Ftraffic%2Dsigns%2Ddetection1%2Ezip' \
  -H 'accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/jxl,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'accept-language: en-US,en;q=0.9' \
  -H 'cookie: FedAuth=77u/PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz48U1A+VjE0LDBoLmZ8bWVtYmVyc2hpcHx1cm4lM2FzcG8lM2F0ZW5hbnRhbm9uIzc3ZTE4Yjg3LTUxZDMtNDllMS1iMjgxLWRmZGE1YTkyNjA2MSwwIy5mfG1lbWJlcnNoaXB8dXJuJTNhc3BvJTNhdGVuYW50YW5vbiM3N2UxOGI4Ny01MWQzLTQ5ZTEtYjI4MS1kZmRhNWE5MjYwNjEsMTM0MDA2OTUxMDQwMDAwMDAwLDAsMTM0MDA3ODEyMDQ3MjI4NDM3LDAuMC4wLjAsMjU4LDc3ZTE4Yjg3LTUxZDMtNDllMS1iMjgxLWRmZGE1YTkyNjA2MSwsLGRjOTFiZmExLTUwMDktNTAwMC1jZmYyLTA4ZWZmMDViZWQwZCxkYzkxYmZhMS01MDA5LTUwMDAtY2ZmMi0wOGVmZjA1YmVkMGQsVktaQVordmFEVWlIQXM0dzh3UGpjUSwwLDAsMCwsLCwyNjUwNDY3NzQzOTk5OTk5OTk5LDAsLCwsLCwsMCwsMTk2MDEwLHJMSFBYbWZOcnlzVVBfZ3hrbzd1VzJoSnRaMCwsT1cvM0hnMnlyanlFL2hMTmtsbkdTRFlsOTN2cXk5enN5VjgxUUhXdmtYNFQxQ3ErUitCd3MxRCtrTVhkbXFTTldvYUR6NWpNR0pFSUV3U3BUMERuWThyV1pJRlpsN0czaDR4SHBVaEFPY3RmR080b2t3SmlJS2Z3aEhsY2FHRDhTVU15SVpHM09nL3dPaEFkbzQ4Zm56NWkvNEwveHg1cTNWd1ZYc042N2t2aHcvRWFMYzlZTGhnUUluOE91NGxISzVJVEpJVXJJZUFaNzRPWEk4L1AvSVFYYWwrazIrOUcvVmhPYTFVR2JBRUx3STBaSGNERDJ4OURjd0trRnJVZ0NFYzNzQjNXQ0FMVmZOOUJlQUE5aDEvT1lmM1JvZ1VzeGZZMW9Na1R0QnljY0dFeTYyRHMyZ2swOXNlNlYrdWRHUXVJaWFCQklhSjB3R3hCTHlETjV3PT08L1NQPg==; FeatureOverrides_experiments=[]; ai_session=Zg8M8wAv7O597YTsPRGE8J|1756221205576|1756221205582; msal.cache.encryption=%7B%22id%22%3A%220198e6f0-ecee-7195-a5df-9106006eb99b%22%2C%22key%22%3A%22GHHVlHrYgLTSRdSeIVTriknGlhFIDjNUsLhtH8CPZx0%22%7D; MSFPC=GUID=d8c9ad9249d546dcbc3af2f985a840bf&HASH=d8c9&LV=202508&V=4&LU=1756221212157' \
  -H 'dnt: 1' \
  -H 'priority: u=0, i' \
  -H 'referer: https://ueeduph-my.sharepoint.com/personal/concepcion_timothyjames_ue_edu_ph/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets%2Ftraffic%2Dsigns%2Ddetection1%2Ezip&parent=%2Fpersonal%2Fconcepcion%5Ftimothyjames%5Fue%5Fedu%5Fph%2FDocuments%2Fshared%2Fthesis%2Fdatasets&ga=1' \
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
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36' --output traffic-signs-detection1.zip
# unzip traffic-signs-detection1.zip
unzip traffic-signs-detection1.zip
# remove zip file
rm traffic-signs-detection1.zip