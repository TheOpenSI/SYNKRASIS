import json, re
from pathlib import Path

files = list(Path(__file__).parent.glob("phi4-r*"))

with open(files[0], "r") as f:
    data = json.load(f)
    corr_count = 0
    
for data_point in data:
    data_point["ref_predicted_label"] = data_point["predicted_label"].split("/think>")[-1].strip()
    refined_predicted_label = re.search(
                                        # r"</think>\s*(service\s[a-zA-Z_]+)",
                                        r".*(service\s[a-zA-Z_]+|[Ss]ervice\s-1|:\s+[a-z_]+).*",
                                        data_point["ref_predicted_label"], 
                                        re.DOTALL)

    data_point["ref_predicted_label"] = refined_predicted_label.group(1) if refined_predicted_label else "service -1"
    data_point["is_correct"] = True if data_point["true_label"] in data_point["ref_predicted_label"] else False
    
    if data_point["is_correct"]:
        corr_count += 1
    
    with open(str(files[0]).replace(".json", "_refined.json"), "w") as f:
        json.dump(data, f, indent=4)
        
print(f"Accuracy: {corr_count}/{len(data)} = {corr_count/len(data)}")

# =======================================================================================================================

with open(files[2], "r") as f:
    data = json.load(f)
    corr_count = 0
    
for data_point in data:
    data_point["ref_predicted_label"] = data_point["predicted_label"].split("/think>")[-1].strip()
    refined_predicted_label = re.search(
                                        # r"</think>\s*(service\s[a-zA-Z_]+)",
                                        r".*(service\s[a-zA-Z_]+|[Ss]ervice\s-1|:\s+[a-z_]+).*",
                                        data_point["ref_predicted_label"], 
                                        re.DOTALL)
    
    if refined_predicted_label:
        data_point["ref_predicted_label"] = refined_predicted_label.group(1)
        
    else:
        if len(data_point["ref_predicted_label"].split(" ")) == 1:
            data_point["ref_predicted_label"] = data_point["ref_predicted_label"]
        
        else:
            if match := re.search(r"[a-z]+_[a-z_]{2,}", data_point["ref_predicted_label"], re.DOTALL):
                data_point["ref_predicted_label"] = match.group(0)
            else:
                # print(data_point["ref_predicted_label"])
                data_point["ref_predicted_label"] = "service -1"

    # data_point["ref_predicted_label"] = refined_predicted_label.group(1) if refined_predicted_label else "service -1"
    data_point["is_correct"] = True if data_point["true_label"] in data_point["ref_predicted_label"] else False
    
    if data_point["is_correct"]:
        corr_count += 1
    
    with open(str(files[2]).replace(".json", "_refined.json"), "w") as f:
        json.dump(data, f, indent=4)
        
print(f"Accuracy: {corr_count}/{len(data)} = {corr_count/len(data)}")