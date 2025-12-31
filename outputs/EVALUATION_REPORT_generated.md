# Agentic Threat Hunt Evaluation Report

## Overall Performance

| Metric | Value | Definition |
| :--- | :--- | :--- |
| **Success Rate** | 100.0% | % of hunts returning results |
| **Schema Faithfulness** | 79.9% | Adherence to CloudTrail schema |
| **Avg Latency** | 12.78s | Speed per hypothesis |

## Hunt Breakdown

| ID | Hypothesis | Status | Rows | Faithfulness |
| :--- | :--- | :--- | :--- | :--- |
| 1 | CloudTrail logs contain failed console login attem... | ✅ PASS | 5 | 77.8% |
| 2 | Root user console login attempts can be identified... | ✅ PASS | 5 | 75.0% |
| 3 | Adversaries may attempt to disrupt CloudTrail logg... | ✅ PASS | 3 | 83.3% |
| 4 | Unauthorized API calls (AccessDenied or Unauthoriz... | ✅ PASS | 2 | 66.7% |
| 5 | Attackers use GetCallerIdentity API calls (similar... | ✅ PASS | 3 | 75.0% |
| 6 | Adversaries may attempt to retrieve secrets (certi... | ✅ PASS | 2 | 85.7% |
| 7 | Attackers may attempt to launch extra-large EC2 in... | ✅ PASS | 3 | 80.0% |
| 8 | Attackers may brute force S3 bucket names by attem... | ✅ PASS | 2 | 60.0% |
| 9 | CloudTrail logs contain requests from suspicious u... | ✅ PASS | 4 | 100.0% |
| 9 | CloudTrail logs contain requests from suspicious u... | ✅ PASS | 3 | 100.0% |
| 10 | CreateAccessKey events from IAM users (not roles) ... | ✅ PASS | 3 | 75.0% |
