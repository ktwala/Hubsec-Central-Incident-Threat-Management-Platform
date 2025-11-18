# API Testing Guide - New Endpoints

## Overview

This guide shows how to test the newly implemented API endpoints for Source Systems, Assets, and Playbooks.

## Prerequisites

1. PostgreSQL database initialized with sample data
2. Multi-tenant API running
3. User and Tenant UUIDs from database

```bash
# Set environment
export DATABASE_URL="postgresql://hubsec:hubsec@localhost/hubsec_multitenant"

# Start the API
uvicorn backend.app.main_multitenant:app --reload
```

## Get Test Data UUIDs

```bash
# Get Hubsec Analyst User ID
export USER_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM users WHERE username='hubsec_analyst1';" | tr -d ' ')

# Get Econet Tenant ID
export ECONET_TENANT=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM tenants WHERE code='ECONET';" | tr -d ' ')

# Get PostBank Tenant ID
export POSTBANK_TENANT=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM tenants WHERE code='POSTBANK';" | tr -d ' ')
```

---

## Source Systems API

### 1. List All Source Systems

```bash
curl -X GET "http://localhost:8000/api/v1/source-systems" \
  -H "X-User-ID: $USER_ID"
```

**Expected Response**: List of all source systems across all tenants

### 2. Filter Source Systems by Tenant

```bash
curl -X GET "http://localhost:8000/api/v1/source-systems?tenant_id=$ECONET_TENANT" \
  -H "X-User-ID: $USER_ID"
```

**Expected Response**: Only Econet's source systems

### 3. Filter by Integration Type

```bash
curl -X GET "http://localhost:8000/api/v1/source-systems?integration_type=wazuh" \
  -H "X-User-ID: $USER_ID"
```

**Expected Response**: Only Wazuh instances

### 4. Create New Source System

```bash
curl -X POST "http://localhost:8000/api/v1/source-systems" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$ECONET_TENANT\",
    \"name\": \"Econet CrowdStrike\",
    \"type\": \"crowdstrike\",
    \"description\": \"CrowdStrike EDR for Econet\",
    \"base_url\": \"https://api.crowdstrike.com\",
    \"auth_type\": \"api_key\",
    \"auth_config\": {\"api_key\": \"test_key\"},
    \"is_active\": true,
    \"config\": {\"region\": \"us-east-1\"}
  }"
```

**Expected Response**: Created source system with UUID

### 5. Get Source System by ID

```bash
# Get first source system ID
export SOURCE_SYSTEM_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM source_systems LIMIT 1;" | tr -d ' ')

curl -X GET "http://localhost:8000/api/v1/source-systems/$SOURCE_SYSTEM_ID" \
  -H "X-User-ID: $USER_ID"
```

### 6. Update Source System

```bash
curl -X PATCH "http://localhost:8000/api/v1/source-systems/$SOURCE_SYSTEM_ID" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"description\": \"Updated description\",
    \"sync_status\": \"healthy\"
  }"
```

### 7. Trigger Sync

```bash
curl -X POST "http://localhost:8000/api/v1/source-systems/$SOURCE_SYSTEM_ID/sync" \
  -H "X-User-ID: $USER_ID"
```

**Expected Response**: Sync triggered message

### 8. Check Health

```bash
curl -X GET "http://localhost:8000/api/v1/source-systems/$SOURCE_SYSTEM_ID/health" \
  -H "X-User-ID: $USER_ID"
```

---

## Assets API

### 1. List All Assets

```bash
curl -X GET "http://localhost:8000/api/v1/assets" \
  -H "X-User-ID: $USER_ID"
```

### 2. Filter Assets by Type

```bash
curl -X GET "http://localhost:8000/api/v1/assets?asset_type=server" \
  -H "X-User-ID: $USER_ID"
```

### 3. Filter by Criticality

```bash
curl -X GET "http://localhost:8000/api/v1/assets?criticality=critical" \
  -H "X-User-ID: $USER_ID"
```

### 4. Search Assets

```bash
curl -X GET "http://localhost:8000/api/v1/assets?search=web" \
  -H "X-User-ID: $USER_ID"
```

**Expected**: Assets with "web" in hostname or IP

### 5. Create New Asset

```bash
curl -X POST "http://localhost:8000/api/v1/assets" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$ECONET_TENANT\",
    \"hostname\": \"econet-api-01\",
    \"ip_address\": \"192.168.20.10\",
    \"mac_address\": \"00:1A:2B:3C:4D:5F\",
    \"asset_type\": \"server\",
    \"criticality\": \"high\",
    \"os\": \"Ubuntu 22.04 LTS\",
    \"environment\": \"production\",
    \"owner\": \"API Team\",
    \"department\": \"Engineering\",
    \"location\": \"Harare DC2\",
    \"is_active\": true,
    \"tags\": [\"api\", \"production\", \"rest\"]
  }"
```

### 6. Get Asset by ID

```bash
export ASSET_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM assets LIMIT 1;" | tr -d ' ')

curl -X GET "http://localhost:8000/api/v1/assets/$ASSET_ID" \
  -H "X-User-ID: $USER_ID"
```

### 7. Update Asset

```bash
curl -X PATCH "http://localhost:8000/api/v1/assets/$ASSET_ID" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"criticality\": \"critical\",
    \"tags\": [\"database\", \"pci\", \"production\"]
  }"
```

### 8. Asset Heartbeat

```bash
curl -X POST "http://localhost:8000/api/v1/assets/$ASSET_ID/heartbeat" \
  -H "X-User-ID: $USER_ID"
```

**Expected**: Updates last_seen timestamp

### 9. Get Asset Alerts

```bash
curl -X GET "http://localhost:8000/api/v1/assets/$ASSET_ID/alerts" \
  -H "X-User-ID: $USER_ID"
```

**Expected**: All alerts associated with this asset

---

## Playbooks API

### 1. List All Playbooks

```bash
curl -X GET "http://localhost:8000/api/v1/playbooks" \
  -H "X-User-ID: $USER_ID"
```

**Expected**: Global playbooks + user's tenant playbooks

### 2. List Only Global Playbooks

```bash
curl -X GET "http://localhost:8000/api/v1/playbooks?include_global=true" \
  -H "X-User-ID: $USER_ID"
```

### 3. Filter by Incident Type

```bash
curl -X GET "http://localhost:8000/api/v1/playbooks?incident_type=ransomware" \
  -H "X-User-ID: $USER_ID"
```

### 4. Create Global Playbook (Super Admin Only)

```bash
# Get super admin ID
export ADMIN_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM users WHERE username='superadmin';" | tr -d ' ')

curl -X POST "http://localhost:8000/api/v1/playbooks" \
  -H "X-User-ID: $ADMIN_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": null,
    \"name\": \"Phishing Response\",
    \"description\": \"Standard phishing incident response procedure\",
    \"incident_type\": \"phishing\",
    \"definition\": {
      \"steps\": [
        {\"id\": 1, \"action\": \"Quarantine email\", \"type\": \"manual\"},
        {\"id\": 2, \"action\": \"Block sender\", \"type\": \"automation\"},
        {\"id\": 3, \"action\": \"Notify users\", \"type\": \"manual\"}
      ]
    },
    \"version\": \"1.0\",
    \"is_active\": true,
    \"tags\": [\"phishing\", \"email\", \"global\"]
  }"
```

### 5. Create Tenant Playbook

```bash
curl -X POST "http://localhost:8000/api/v1/playbooks" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": \"$ECONET_TENANT\",
    \"name\": \"Econet Data Breach Response\",
    \"description\": \"Econet-specific data breach procedure\",
    \"incident_type\": \"data_breach\",
    \"definition\": {
      \"steps\": [
        {\"id\": 1, \"action\": \"Isolate affected systems\", \"type\": \"manual\"},
        {\"id\": 2, \"action\": \"Notify legal team\", \"type\": \"manual\"},
        {\"id\": 3, \"action\": \"Activate PR plan\", \"type\": \"manual\"}
      ]
    },
    \"version\": \"1.0\",
    \"is_active\": true,
    \"tags\": [\"data-breach\", \"econet\"]
  }"
```

### 6. Get Playbook by ID

```bash
export PLAYBOOK_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM playbooks LIMIT 1;" | tr -d ' ')

curl -X GET "http://localhost:8000/api/v1/playbooks/$PLAYBOOK_ID" \
  -H "X-User-ID: $USER_ID"
```

### 7. Update Playbook

```bash
curl -X PATCH "http://localhost:8000/api/v1/playbooks/$PLAYBOOK_ID" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"version\": \"1.1\",
    \"description\": \"Updated playbook description\"
  }"
```

### 8. Attach Playbook to Case (Start Execution)

```bash
# Get a case ID
export CASE_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM cases LIMIT 1;" | tr -d ' ')

curl -X POST "http://localhost:8000/api/v1/playbooks/execute" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"case_id\": \"$CASE_ID\",
    \"playbook_id\": \"$PLAYBOOK_ID\",
    \"status\": \"in_progress\"
  }"
```

**Expected**: Creates case_playbook execution record

### 9. Update Playbook Execution

```bash
export CASE_PLAYBOOK_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM case_playbooks LIMIT 1;" | tr -d ' ')

curl -X PATCH "http://localhost:8000/api/v1/playbooks/executions/$CASE_PLAYBOOK_ID" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"current_step\": 2,
    \"status\": \"in_progress\",
    \"meta_data\": {\"notes\": \"Completed step 1\"}
  }"
```

### 10. Get Playbooks for a Case

```bash
curl -X GET "http://localhost:8000/api/v1/playbooks/executions/case/$CASE_ID" \
  -H "X-User-ID: $USER_ID"
```

**Expected**: All playbook executions for the case

---

## Access Control Tests

### Test 1: Tenant Isolation (Should Fail)

```bash
# Get PostBank admin user
export POSTBANK_USER=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM users WHERE username='postbank_admin';" | tr -d ' ')

# Try to access Econet source system
curl -X GET "http://localhost:8000/api/v1/source-systems/$SOURCE_SYSTEM_ID" \
  -H "X-User-ID: $POSTBANK_USER"
```

**Expected**: 403 Forbidden - "Access denied to this source system"

### Test 2: Global Playbook Creation (Should Fail)

```bash
# Try to create global playbook as regular user
curl -X POST "http://localhost:8000/api/v1/playbooks" \
  -H "X-User-ID: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"tenant_id\": null,
    \"name\": \"Test Global\",
    \"incident_type\": \"test\",
    \"definition\": {\"steps\": []}
  }"
```

**Expected**: 403 Forbidden - "Only super admins can create global playbooks"

---

## API Documentation

Once the API is running, visit:

**Swagger UI**: http://localhost:8000/api/docs

This provides:
- Interactive API testing
- Schema documentation
- Example requests/responses
- Authentication testing

---

## Complete Test Script

```bash
#!/bin/bash

# Set environment
export DATABASE_URL="postgresql://hubsec:hubsec@localhost/hubsec_multitenant"

# Get test UUIDs
export USER_ID=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM users WHERE username='hubsec_analyst1';" | tr -d ' ')
export ECONET_TENANT=$(psql -U hubsec -d hubsec_multitenant -t -c "SELECT id FROM tenants WHERE code='ECONET';" | tr -d ' ')

echo "Testing Source Systems API..."
curl -s -X GET "http://localhost:8000/api/v1/source-systems" \
  -H "X-User-ID: $USER_ID" | jq '.[] | {name, type, sync_status}'

echo -e "\nTesting Assets API..."
curl -s -X GET "http://localhost:8000/api/v1/assets" \
  -H "X-User-ID: $USER_ID" | jq '.[] | {hostname, asset_type, criticality}'

echo -e "\nTesting Playbooks API..."
curl -s -X GET "http://localhost:8000/api/v1/playbooks" \
  -H "X-User-ID: $USER_ID" | jq '.[] | {name, incident_type, version}'

echo -e "\nAll tests completed!"
```

Save as `test_api.sh`, make executable with `chmod +x test_api.sh`, and run.

---

## Troubleshooting

### Error: "Authentication required"

**Solution**: Make sure you're passing a valid `X-User-ID` header

### Error: "Tenant not found"

**Solution**: Verify the tenant_id UUID is correct

### Error: "Access denied"

**Solution**: Check that the user has access to the specified tenant

### No Results Returned

**Solution**: Make sure you've initialized the database with sample data:
```bash
python scripts/init_db_multitenant.py --database-url "$DATABASE_URL" --drop --seed
```

---

## Summary

You now have 3 fully functional API endpoint groups:

✅ **Source Systems** (7 endpoints) - Integration management
✅ **Assets** (9 endpoints) - IT asset inventory
✅ **Playbooks** (10 endpoints) - Automation & runbooks

**Total**: 26 new API endpoints with full CRUD, filtering, and access control!
