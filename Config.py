import os

# https://readonlyrest.atlassian.net/sr/jira.issueviews:searchrequest-xml/temp/SearchRequest.xml?jqlQuery=project+%3D+%22RORDEV%22+ORDER+BY+created+DESC&atl_token=f3ad25f0-2232-4ec5-a31e-0e16a00f1ee0_08a7c1d4d1703d7f6b8fe341d7299b710fd6268b_lin&tempMax=1000
JIRA_RSS_EXPORT_FILE = "./all_tasks.xml"

# https://YOUR_ORG.jetbrains.space
SPACES_URL = "https://beshu.jetbrains.space"

SPACES_PROJECT_ID = "23tkZF01SLKP"  # pick this up from API playground prepopulated values (see below URL)

# You get this from https://YOUR_ORG.jetbrains.space/extensions/installedApplications/<NEW_APP_YOU_MUST_CREATE>/permanent-tokens
# Or even better, as a owner, generate your personal token.
API_AUTH_TOKEN = os.getenv("TOKEN")

JIRA_ISSUE_ID_PREFIX = "RORDEV-"
JIRA_STATUS_TO_SPACE_STATUS_ID = {
    # grep "<status"  all_tasks.xml | grep -vi done | grep -v "&lt"| sed -e 's/<[^>]*>//g' | sort | uniq
    "To Do": "3mLmz93RuAl9",  # Open
    "Done": "16PG4L15G4L9",
    "In Progress": "4D8I5A3s5JqE",
    "ON HOLD": "4dOimM2cKncz",
    "REJECTED": "16PG4L15G4L9"
}

JIRA_LABEL_TO_SPACE_TAG_ID = {
    "ror_es": "20vaFW1wT1mm",
    "NP": "vCDCh0lyLzc",
    "Portal": "Jil1r1Yt110",
    "kibana": "2Fndl91iVhfT"
}
CACHE_DIR = "./cache"
