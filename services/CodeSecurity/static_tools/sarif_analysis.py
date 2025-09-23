import json

with open('services/CodeSecurity/static_tools/results.sarif', 'r') as f:
    sarif_data = json.load(f)

results = sarif_data.get('runs', [{}])[0].get('results', [])

print(f"Total issues found: {len(results)}")
for result in results:
    rule_id = result.get('ruleId', 'N/A')
    message = result.get('message', {}).get('text', 'N/A')
    locations = result.get('locations', [])
    if locations:
        physical_location = locations[0].get('physicalLocation', {})
        artifact_location = physical_location.get('artifactLocation', {})
        file_path = artifact_location.get('uri', 'N/A')
        region = physical_location.get('region', {})
        start_line = region.get('startLine', 'N/A')
        start_column = region.get('startColumn', 'N/A')
    else:
        file_path = 'N/A'
        start_line = 'N/A'
        start_column = 'N/A'
    
    print(f"Issue: {rule_id}")
    print(f"Message: {message}")
    print(f"File: {file_path}, Line: {start_line}, Column: {start_column}")
    print("-" * 40)
