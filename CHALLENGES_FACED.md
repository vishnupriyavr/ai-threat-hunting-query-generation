# Step by step approach - Challenges faced

I. Perform EDA on the dataset to get an idea of how the logs are distributed.

II. Based on the hypotheses.json file and the columns in the dataset, here is a breakdown of which columns relate to each hypothesis:

  1. Sign-in Failures (Brute Force/Bot Attacks)
   * eventName: Look for values like ConsoleLogin.
   * eventType: Should be AwsConsoleSignIn.
   * errorMessage: Will indicate failure, e.g., "Failed authentication".
   * errorCode: Will contain the error code for the failure.
   * sourceIPAddress: To identify the source of the attacks.
   * eventTime: To analyze the timing and frequency of attacks.

  2. Root Access Through Console
   * userIdentitytype: Look for the value Root.
   * userIdentityarn: The ARN of the user, which will contain :root.
   * eventName: Should be ConsoleLogin or similar.
   * eventType: Should be AwsConsoleSignIn.
   * sourceIPAddress: To see where the root login attempt is coming from.

  3. CloudTrail Disruption
   * eventName: Look for values like StopLogging, DeleteTrail, UpdateTrail.
   * eventSource: Should be cloudtrail.amazonaws.com.
   * userIdentitytype, userIdentityprincipalId, userIdentityarn: To identify who attempted to disrupt logging.

  4. Unauthorized API Calls
   * errorCode: Look for AccessDenied or UnauthorizedOperation.
   * errorMessage: Provides details about the failed call.
   * eventName: The API call that was attempted.
   * sourceIPAddress: The source of the unauthorized call.
   * userIdentitytype, userIdentityprincipalId, userIdentityarn: To identify who made the unauthorized call.

  5. Whoami Reconnaissance
   * eventName: Look for GetCallerIdentity.
   * eventSource: Should be sts.amazonaws.com.
   * sourceIPAddress: Source of the reconnaissance activity.
   * userIdentitytype, userIdentityprincipalId, userIdentityarn: To see who is performing the check.

  6. Secrets Manager Access
   * eventSource: Look for secretsmanager.amazonaws.com.
   * eventName: Look for events like GetSecretValue.
   * userIdentitytype, userIdentityprincipalId, 'userIdentityarn`: To identify who is trying to access secrets.

  7. Large EC2 Instance Creation
   * eventName: Should be RunInstances.
   * eventSource: Should be ec2.amazonaws.com.
   * requestParametersinstanceType: The key column. Look for large instance sizes (e.g., *.10xlarge or bigger).

  8. S3 Bucket Brute Force
   * eventName: Look for GetBucketAcl.
   * eventSource: Should be s3.amazonaws.com.
   * errorCode: NoSuchBucket indicates a failed attempt on a non-existent bucket.
   * sourceIPAddress: To identify if many requests are coming from a single IP.

  9. Suspicious User Agents
   * userAgent: This is the primary column. You would search for substrings like kali, parrot, powershell, or command/*.

  10. Permanent Key Creation
   * eventName: Look for CreateAccessKey.
   * eventSource: Should be iam.amazonaws.com.
   * userIdentitytype: Should be IAMUser (to distinguish from temporary keys created for roles).

III. The core challenge of this project is bridging the significant semantic gap between abstract, human-readable threat hypotheses (e.g., "an adversary attempts to disrupt CloudTrail") and the specific, low-level event data required to find evidence of that threat (e.g., eventName = 'StopLogging' AND eventSource = 'cloudtrail.amazonaws.com').

  A Knowledge Graph is the ideal architecture to solve this problem for the following reasons:

  1. It Models Complex Relationships, Not Just Keywords.
  A simple rule-based or keyword-mapping system would be brittle. For instance, "CloudTrail Disruption" could involve multiple
  events (StopLogging, DeleteTrail, UpdateTrail). A KG represents the relationship between the abstract concept of "Defense
  Evasion" and the concrete API calls that implement it. This allows the query generation system to be far more comprehensive and
  resilient to changes. The presence of init_ontology.cql and Neo4j scripts in your project indicates this is a primary goal.

  2. It Centralizes Domain Knowledge.
  The AWS ecosystem is vast and constantly evolving. A KG provides a structured, centralized repository to formally encode this
  domain knowledge:
   * Entities: IAM Users, EC2 Instances, S3 Buckets, API Calls.
   * Relationships: An IAMUser can perform an APICall; an APICall can target a Resource; an EC2Instance has an InstanceType.
   * Attributes: An InstanceType has a size; an APICall can have an errorCode.

  This turns raw strings from your dataset (eventName, userIdentitytype, etc.) into rich, interconnected entities, making the
  data "smarter".

  3. It Enables More Flexible and Intelligent Query Generation.
  Instead of writing a hardcoded query for each hypothesis, the system can traverse the graph. To find evidence for "Large EC2
  Instance Creation," the query generator can:
   1. Find the "Large EC2 Instance" node in the KG.
   2. Follow relationships to identify the corresponding eventName (RunInstances).
   3. Follow further relationships to identify which column contains instance size (requestParametersinstanceType) and what
      values are considered "large" (e.g., > 8xlarge).

  This makes the system highly adaptable. Adding a new instance type or threat technique only requires updating the graph, not
  the query generation code.

  4. It Separates "What" from "How".
  The KG describes what the relationships are in the threat landscape (the "what"). The query generation code focuses on how to
  translate a path through that graph into an executable query. This separation makes the system cleaner, more modular, and
  easier to maintain and expand. You can update your understanding of threats (the KG) without rewriting the logic that generates
  queries.

  In summary, a Knowledge Graph transforms the query generation process from a brittle, rule-based matching exercise into an
  intelligent traversal of a rich, semantic model of your domain. It is the most effective way to translate high-level, human
  intent into precise, machine-executable queries against your dataset.

IV. One of the major challenges with this kind of dataset is missing values.

For threat hunting in logs, simply removing rows with missing values is dangerous. A missing value is often a
  piece of evidence in itself. For example:
   * A missing errorCode implies the API call was successful.
   * A missing userIdentityuserName could indicate an action taken by the Root user or a service.

  The best solution is not to remove the data, but to make the query generation logic "null-aware". The agent responsible for creating the SQL queries should understand the context of a missing value for each threat hypothesis.

Adopting this "null-aware" approach has a significant and positive impact on query generation:

   1. Increased Query Precision: The queries become much more specific and effective. Instead of just looking for a value (WHERE eventName = 'ConsoleLogin'), we can look for the presence or absence of other values to home in on the exact threat.

       * Example (Hypothesis 1): To find failed logins, the query should be:
          WHERE eventName = 'ConsoleLogin' AND errorCode IS NOT NULL
       * Example (Hypothesis 2): To find successful root logins, the query would be the opposite:
          WHERE eventName = 'ConsoleLogin' AND userIdentitytype = 'Root' AND errorCode IS NULL

   2. Avoids Data Loss: We preserve all events in the dataset. A successful API call (where errorCode is null) might be a crucial step in a larger attack chain, and removing it during a pre-processing step would make that chain invisible.

   3. Enriches the Knowledge Graph's Role: This is a perfect use case for the Knowledge Graph. The KG can be designed to store the logic for handling nulls. For instance, it can model that for a CreateAccessKey event, an errorCode of NULL is an indicator of Success. The query generator can then use this information from the KG to construct the correct, context-aware SQL query automatically.