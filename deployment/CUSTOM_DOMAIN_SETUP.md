# Custom Domain Setup: mcp.simonkennedymp.com.au

## Overview

This guide explains how to set up `mcp.simonkennedymp.com.au` as a custom domain for your Cloud Run service.

**Recommended**: Use Cloud Run Domain Mapping (Option 1) for simplicity and automatic SSL.

---

## Option 1: Cloud Run Domain Mapping (Recommended)

### Prerequisites
- Cloud Run service deployed
- Domain ownership of `simonkennedymp.com.au`
- Access to DNS records at your domain registrar

### Step 1: Deploy Cloud Run Service

```bash
# Set project
export PROJECT_ID="skai-fastmcp-cloudrun"
gcloud config set project $PROJECT_ID

# Deploy service (initial deployment)
gcloud run deploy hansard-mcp-server \
    --image gcr.io/$PROJECT_ID/hansard-mcp-server:latest \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars GCP_PROJECT_ID=$PROJECT_ID \
    --set-env-vars FASTMCP_SERVER_BASE_URL=https://mcp.simonkennedymp.com.au
```

**Note the service URL**: `https://hansard-mcp-server-<hash>-uc.a.run.app`

### Step 2: Create Domain Mapping

```bash
# Map custom domain to Cloud Run service
gcloud run domain-mappings create \
    --service hansard-mcp-server \
    --domain mcp.simonkennedymp.com.au \
    --region us-central1 \
    --project skai-fastmcp-cloudrun
```

**Output will show**:
```
✓ Creating domain mapping...
  ✓ Mapping to Cloud Run service
  Waiting for certificate provisioning. You must configure your DNS records
  for certificate issuance to begin.

  Please add the following DNS records to your domain registrar:

  NAME                       TYPE  DATA
  mcp.simonkennedymp.com.au  A     216.239.32.21
  mcp.simonkennedymp.com.au  A     216.239.34.21
  mcp.simonkennedymp.com.au  A     216.239.36.21
  mcp.simonkennedymp.com.au  A     216.239.38.21
  mcp.simonkennedymp.com.au  AAAA  2001:4860:4802:32::15
  mcp.simonkennedymp.com.au  AAAA  2001:4860:4802:34::15
  mcp.simonkennedymp.com.au  AAAA  2001:4860:4802:36::15
  mcp.simonkennedymp.com.au  AAAA  2001:4860:4802:38::15
```

### Step 3: Add DNS Records

**At your domain registrar** (where you manage `simonkennedymp.com.au`):

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | mcp | 216.239.32.21 | 3600 |
| A | mcp | 216.239.34.21 | 3600 |
| A | mcp | 216.239.36.21 | 3600 |
| A | mcp | 216.239.38.21 | 3600 |
| AAAA | mcp | 2001:4860:4802:32::15 | 3600 |
| AAAA | mcp | 2001:4860:4802:34::15 | 3600 |
| AAAA | mcp | 2001:4860:4802:36::15 | 3600 |
| AAAA | mcp | 2001:4860:4802:38::15 | 3600 |

**Common Registrars**:
- **GoDaddy**: DNS → Manage → Add Record
- **Namecheap**: Advanced DNS → Add New Record
- **Route 53 (AWS)**: Hosted Zones → Create Record
- **Cloudflare**: DNS → Add Record

**Note**: If using Cloudflare, disable the orange cloud (proxy) for this record initially.

### Step 4: Verify Domain Ownership

```bash
# Check domain mapping status
gcloud run domain-mappings describe \
    --domain mcp.simonkennedymp.com.au \
    --region us-central1 \
    --project skai-fastmcp-cloudrun
```

**Expected output**:
```yaml
status:
  conditions:
  - status: "True"
    type: Ready
  - message: "Certificate provisioned."
    status: "True"
    type: CertificateProvisioned
```

### Step 5: SSL Certificate Provisioning

**Google automatically provisions a free SSL certificate** using Let's Encrypt.

- **Provisioning time**: 15 minutes to 24 hours
- **Automatic renewal**: Every 90 days
- **Protocol**: TLS 1.2 and 1.3

**Check certificate status**:
```bash
gcloud run domain-mappings describe \
    --domain mcp.simonkennedymp.com.au \
    --region us-central1 \
    --format="value(status.conditions)"
```

Wait for `CertificateProvisioned: True`

### Step 6: Test Custom Domain

```bash
# Test DNS resolution
dig mcp.simonkennedymp.com.au

# Test HTTPS endpoint
curl -I https://mcp.simonkennedymp.com.au

# Test FastMCP server
curl https://mcp.simonkennedymp.com.au/health
```

### Step 7: Update GitHub OAuth Callback

**Update GitHub OAuth App** at https://github.com/settings/developers:

| Field | Value |
|-------|-------|
| Authorization callback URL | `https://mcp.simonkennedymp.com.au/auth/callback` |

---

## Option 2: Cloud Load Balancer + CDN (Advanced)

Use this if you need:
- Global CDN for faster worldwide access
- Custom SSL certificates (not Let's Encrypt)
- Advanced routing (URL rewriting, redirects)
- DDoS protection via Cloud Armor

### Cost Estimate
- Load Balancer: $18/month (minimum)
- Cloud CDN: $0.02-0.08/GB egress
- SSL Certificate: Free (Google-managed) or $0 (bring your own)

### Setup Steps

```bash
# 1. Create serverless NEG for Cloud Run
gcloud compute network-endpoint-groups create hansard-neg \
    --region=us-central1 \
    --network-endpoint-type=serverless \
    --cloud-run-service=hansard-mcp-server \
    --project=skai-fastmcp-cloudrun

# 2. Create backend service
gcloud compute backend-services create hansard-backend \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --enable-cdn \
    --project=skai-fastmcp-cloudrun

# 3. Add NEG to backend
gcloud compute backend-services add-backend hansard-backend \
    --global \
    --network-endpoint-group=hansard-neg \
    --network-endpoint-group-region=us-central1 \
    --project=skai-fastmcp-cloudrun

# 4. Create URL map
gcloud compute url-maps create hansard-lb \
    --default-service=hansard-backend \
    --global \
    --project=skai-fastmcp-cloudrun

# 5. Reserve static IP
gcloud compute addresses create hansard-ip \
    --global \
    --ip-version=IPV4 \
    --project=skai-fastmcp-cloudrun

# Get the IP address
gcloud compute addresses describe hansard-ip \
    --global \
    --format="value(address)" \
    --project=skai-fastmcp-cloudrun

# 6. Create SSL certificate
gcloud compute ssl-certificates create hansard-ssl \
    --domains=mcp.simonkennedymp.com.au \
    --global \
    --project=skai-fastmcp-cloudrun

# 7. Create HTTPS proxy
gcloud compute target-https-proxies create hansard-https-proxy \
    --url-map=hansard-lb \
    --ssl-certificates=hansard-ssl \
    --global \
    --project=skai-fastmcp-cloudrun

# 8. Create forwarding rule
gcloud compute forwarding-rules create hansard-https-rule \
    --address=hansard-ip \
    --global \
    --target-https-proxy=hansard-https-proxy \
    --ports=443 \
    --project=skai-fastmcp-cloudrun
```

**DNS Setup** (point to static IP):
```
Type: A
Name: mcp
Value: <STATIC_IP_FROM_STEP_5>
```

---

## Troubleshooting

### DNS not resolving

**Check DNS propagation**:
```bash
dig mcp.simonkennedymp.com.au
nslookup mcp.simonkennedymp.com.au
```

**Use Google DNS for testing**:
```bash
dig @8.8.8.8 mcp.simonkennedymp.com.au
```

**DNS propagation can take 24-48 hours**. Test with: https://dnschecker.org

### Certificate provisioning stuck

**Common causes**:
1. DNS records not added correctly
2. DNS not propagated yet (wait 24 hours)
3. CAA records blocking Let's Encrypt

**Check CAA records**:
```bash
dig CAA simonkennedymp.com.au
```

If CAA records exist, ensure they allow Let's Encrypt:
```
simonkennedymp.com.au. 3600 IN CAA 0 issue "letsencrypt.org"
simonkennedymp.com.au. 3600 IN CAA 0 issuewild "letsencrypt.org"
```

### 404 / Service not found

**Verify Cloud Run service is deployed**:
```bash
gcloud run services list --region=us-central1 --project=skai-fastmcp-cloudrun
```

**Check service URL works**:
```bash
curl https://hansard-mcp-server-<hash>-uc.a.run.app
```

### OAuth redirect not working

**Verify callback URL in GitHub OAuth App matches exactly**:
- `https://mcp.simonkennedymp.com.au/auth/callback` (with HTTPS, no trailing slash)

**Check environment variable in Cloud Run**:
```bash
gcloud run services describe hansard-mcp-server \
    --region=us-central1 \
    --format="value(spec.template.spec.containers[0].env)" \
    --project=skai-fastmcp-cloudrun
```

Should show: `FASTMCP_SERVER_BASE_URL=https://mcp.simonkennedymp.com.au`

---

## Security Best Practices

### Enable Cloud Armor (Optional)

Protect against DDoS attacks:

```bash
# Create security policy
gcloud compute security-policies create hansard-security-policy \
    --description="Security policy for Hansard MCP server" \
    --project=skai-fastmcp-cloudrun

# Add rate limiting rule
gcloud compute security-policies rules create 1000 \
    --security-policy=hansard-security-policy \
    --expression="true" \
    --action=rate-based-ban \
    --rate-limit-threshold-count=100 \
    --rate-limit-threshold-interval-sec=60 \
    --ban-duration-sec=600 \
    --project=skai-fastmcp-cloudrun

# Attach to backend service
gcloud compute backend-services update hansard-backend \
    --security-policy=hansard-security-policy \
    --global \
    --project=skai-fastmcp-cloudrun
```

### Enable Cloud CDN Cache

For faster global access:

```bash
# Update backend service to enable CDN
gcloud compute backend-services update hansard-backend \
    --enable-cdn \
    --cache-mode=CACHE_ALL_STATIC \
    --default-ttl=3600 \
    --max-ttl=86400 \
    --global \
    --project=skai-fastmcp-cloudrun
```

---

## Verification Checklist

- [ ] Cloud Run service deployed and responding
- [ ] DNS A/AAAA records added at registrar
- [ ] DNS resolves correctly (`dig mcp.simonkennedymp.com.au`)
- [ ] Domain mapping status shows `Ready: True`
- [ ] SSL certificate provisioned (`CertificateProvisioned: True`)
- [ ] HTTPS endpoint works (`curl https://mcp.simonkennedymp.com.au`)
- [ ] GitHub OAuth callback URL updated
- [ ] OAuth flow works end-to-end

---

## Cost Summary

### Option 1: Cloud Run Domain Mapping
- **Cloud Run**: ~$0 (free tier: 2M requests/month)
- **SSL Certificate**: $0 (Google-managed, auto-renewing)
- **DNS**: Depends on registrar (usually $0-$2/month)
- **Total**: ~$0-$2/month

### Option 2: Cloud Load Balancer + CDN
- **Cloud Run**: ~$0 (free tier)
- **Load Balancer**: $18/month (minimum)
- **Cloud CDN**: $0.02-0.08/GB egress
- **SSL Certificate**: $0 (Google-managed)
- **Total**: ~$20-$50/month (depending on traffic)

**Recommendation**: Start with Option 1 (Domain Mapping). Upgrade to Load Balancer only if you need global CDN or advanced features.

---

**Last Updated**: 2025-10-21
**Project**: skai-fastmcp-cloudrun (666924716777)
**Domain**: mcp.simonkennedymp.com.au
