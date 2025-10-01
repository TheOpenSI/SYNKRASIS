import json
import re
from collections import defaultdict


def extract_cwes_from_field(cwes_field):
    """Extract CWE identifiers from various formats"""
    cwe_set = set()
    cwe_pattern = r'CWE-\d+'
    
    if cwes_field is None:
        return cwe_set
    
    if isinstance(cwes_field, list):
        for item in cwes_field:
            matches = re.findall(cwe_pattern, str(item))
            cwe_set.update(matches)
    elif isinstance(cwes_field, str):
        matches = re.findall(cwe_pattern, cwes_field)
        cwe_set.update(matches)
    
    return cwe_set


def process_tool_results(tool_analysis):
    """Process analysis results from CodeQL or Semgrep"""
    all_cwes = set()
    analysis_results = tool_analysis.get('analysis_results', [])
    
    for result in analysis_results:
        cwes_field = result.get('cwes')
        cwes = extract_cwes_from_field(cwes_field)
        all_cwes.update(cwes)
    
    return list(all_cwes) if all_cwes else None


def process_llm_results(llm_analysis):
    """Process analysis results from LLM"""
    parsed = llm_analysis.get('parsed_response', {})
    cwe_list = parsed.get('cwe', [])
    
    if not cwe_list:
        return None
    
    # Extract CWE codes
    all_cwes = set()
    for cwe in cwe_list:
        matches = re.findall(r'CWE-\d+', str(cwe))
        all_cwes.update(matches)
    
    return list(all_cwes) if all_cwes else None


def normalize_cwe_number(cwe_code):
    """
    Normalize CWE number by removing leading zeros.
    CWE-020 and CWE-20 should be treated as the same.
    """
    if cwe_code.startswith('CWE-'):
        num = cwe_code[4:]
    else:
        num = cwe_code
    
    # Convert to int and back to remove leading zeros
    try:
        return str(int(num))
    except ValueError:
        return num


def build_bidirectional_mapping(cwe_mapping):
    """Build bidirectional CWE relationship mapping with normalized numbers"""
    relationships = defaultdict(set)
    
    for key, related_list in cwe_mapping.items():
        key_num = normalize_cwe_number(key.strip())
        
        for related in related_list:
            related_num = normalize_cwe_number(str(related).strip())
            relationships[key_num].add(related_num)
            relationships[related_num].add(key_num)
        
        for i, cwe1 in enumerate(related_list):
            for cwe2 in related_list[i+1:]:
                cwe1_num = normalize_cwe_number(str(cwe1).strip())
                cwe2_num = normalize_cwe_number(str(cwe2).strip())
                relationships[cwe1_num].add(cwe2_num)
                relationships[cwe2_num].add(cwe1_num)
    
    return relationships


def are_cwes_related(cwe1, cwe2, relationships):
    """Check if two CWE codes are related (with normalization)"""
    num1 = normalize_cwe_number(cwe1)
    num2 = normalize_cwe_number(cwe2)
    
    # Direct match
    if num1 == num2:
        return True
    
    # Check via relationships
    return num2 in relationships.get(num1, set())


def matches_true_label(tool_cwes, true_label, relationships):
    """
    Check if any tool CWE matches the true label.
    Match means: direct match OR related via mapping.
    """
    if tool_cwes is None:
        return False
    
    true_label_num = normalize_cwe_number(true_label)
    
    for cwe in tool_cwes:
        cwe_num = normalize_cwe_number(cwe)
        
        # Direct match
        if cwe_num == true_label_num:
            return True
        
        # Related match via mapping
        if cwe_num in relationships.get(true_label_num, set()):
            return True
    
    return False


def calculate_agreement(cwes1, cwes2, relationships):
    """
    Calculate agreement between two sets of CWEs.
    Returns: ('full', 'partial', or 'none')
    """
    if cwes1 is None or cwes2 is None:
        return None
    
    # Normalize all CWEs
    set1 = set(normalize_cwe_number(c) for c in cwes1)
    set2 = set(normalize_cwe_number(c) for c in cwes2)
    
    # Find all matching pairs (direct or related)
    matched_from_1 = set()
    matched_from_2 = set()
    
    for c1 in set1:
        for c2 in set2:
            if c1 == c2 or c2 in relationships.get(c1, set()):
                matched_from_1.add(c1)
                matched_from_2.add(c2)
    
    if not matched_from_1 and not matched_from_2:
        return 'none'
    
    # Full agreement: all CWEs from both sets are matched
    if matched_from_1 == set1 and matched_from_2 == set2:
        return 'full'
    else:
        return 'partial'


def calculate_multi_agreement(all_cwes_list, relationships):
    """
    Calculate agreement among multiple tools/LLMs.
    all_cwes_list: list of CWE lists from different tools
    Returns: ('full', 'partial', or 'none')
    """
    # Filter out None values
    valid_cwes = [cwes for cwes in all_cwes_list if cwes is not None]
    
    if len(valid_cwes) < 2:
        return None
    
    # Normalize all CWE sets
    normalized_sets = [set(normalize_cwe_number(c) for c in cwes) for cwes in valid_cwes]
    
    # Find CWEs that match across sets (considering relationships)
    all_agreements = []
    
    for i, set_i in enumerate(normalized_sets):
        matched_from_this = set()
        for cwe_i in set_i:
            # Check if this CWE matches with CWEs from ALL other sets
            matches_all = True
            for j, set_j in enumerate(normalized_sets):
                if i == j:
                    continue
                # Check if cwe_i matches any CWE in set_j
                found_match = False
                for cwe_j in set_j:
                    if cwe_i == cwe_j or cwe_j in relationships.get(cwe_i, set()):
                        found_match = True
                        break
                if not found_match:
                    matches_all = False
                    break
            
            if matches_all:
                matched_from_this.add(cwe_i)
        
        all_agreements.append((matched_from_this, set_i))
    
    # Check if any CWEs matched across all sets
    has_any_agreement = any(len(matched) > 0 for matched, _ in all_agreements)
    
    if not has_any_agreement:
        return 'none'
    
    # Check if ALL CWEs from ALL sets are matched
    full_agreement = all(matched == original for matched, original in all_agreements)
    
    if full_agreement:
        return 'full'
    else:
        return 'partial'


def analyse_static_tools(data, cwe_mapping, total_samples):
    """Analyse CodeQL and Semgrep"""
    relationships = build_bidirectional_mapping(cwe_mapping)
    
    stats = {
        'codeql': {'found': 0, 'matched_true': 0},
        'semgrep': {'found': 0, 'matched_true': 0},
        'agreement': {'full': 0, 'partial': 0, 'none': 0, 'both_found': 0}
    }
    
    for entry in data:
        true_label = entry.get('true_label')
        analysis = entry.get('analysis', [])
        
        # Extract CWEs
        codeql_cwes = process_tool_results(analysis[0]) if len(analysis) > 0 else None
        semgrep_cwes = process_tool_results(analysis[1]) if len(analysis) > 1 else None
        
        # Coverage stats
        if codeql_cwes:
            stats['codeql']['found'] += 1
            if matches_true_label(codeql_cwes, true_label, relationships):
                stats['codeql']['matched_true'] += 1
        
        if semgrep_cwes:
            stats['semgrep']['found'] += 1
            if matches_true_label(semgrep_cwes, true_label, relationships):
                stats['semgrep']['matched_true'] += 1
        
        # Agreement stats
        if codeql_cwes and semgrep_cwes:
            stats['agreement']['both_found'] += 1
            agreement = calculate_agreement(codeql_cwes, semgrep_cwes, relationships)
            if agreement:
                stats['agreement'][agreement] += 1
    
    return stats


def analyse_llms(data, cwe_mapping, total_samples):
    """Analyse LLM models"""
    relationships = build_bidirectional_mapping(cwe_mapping)
    
    # Get all unique LLM models
    llm_models = set()
    for entry in data:
        for llm_analysis in entry.get('analysis', []):
            llm_models.add(llm_analysis.get('llm_model'))
    
    llm_models = sorted(list(llm_models))
    
    # Initialize stats
    stats = {
        'models': {},
        'all_agreement': {'full': 0, 'partial': 0, 'none': 0, 'all_found': 0}
    }
    
    for model in llm_models:
        stats['models'][model] = {'found': 0, 'matched_true': 0}
    
    # Process each sample
    for entry in data:
        true_label = entry.get('true_label')
        analysis = entry.get('analysis', [])
        
        # Extract CWEs for each model
        model_cwes = {}
        for llm_analysis in analysis:
            model = llm_analysis.get('llm_model')
            cwes = process_llm_results(llm_analysis)
            model_cwes[model] = cwes
            
            # Coverage stats
            if cwes:
                stats['models'][model]['found'] += 1
                if matches_true_label(cwes, true_label, relationships):
                    stats['models'][model]['matched_true'] += 1
        
        # Multi-way agreement (all LLMs at once)
        all_cwes_list = [model_cwes.get(model) for model in llm_models]
        valid_cwes_count = sum(1 for cwes in all_cwes_list if cwes is not None)
        
        if valid_cwes_count >= 2:  # At least 2 LLMs found something
            if valid_cwes_count == len(llm_models):  # All LLMs found something
                stats['all_agreement']['all_found'] += 1
            
            agreement = calculate_multi_agreement(all_cwes_list, relationships)
            if agreement:
                stats['all_agreement'][agreement] += 1
    
    return stats


def print_static_tool_stats(stats, total_samples):
    """Print statistics for CodeQL and Semgrep"""
    print("=" * 80)
    print("STATIC ANALYSIS TOOLS (CodeQL & Semgrep)")
    print("=" * 80)
    
    for tool in ['codeql', 'semgrep']:
        found = stats[tool]['found']
        matched = stats[tool]['matched_true']
        tool_name = tool.upper()
        
        print(f"\n{tool_name}:")
        print(f"  Found issues for {found} samples out of {total_samples} samples")
        print(f"  Exactly matched true label {matched} times ({matched/total_samples*100:.1f}% of all {total_samples} samples)")
    
    print(f"\n{'='*80}")
    print("AGREEMENT BETWEEN CodeQL AND Semgrep")
    print("="*80)
    
    both_found = stats['agreement']['both_found']
    print(f"\nBoth tools found issues: {both_found} samples")
    
    if both_found > 0:
        full = stats['agreement']['full']
        partial = stats['agreement']['partial']
        none = stats['agreement']['none']
        
        print(f"\nFull agreement (all CWEs match): {full} ({full/both_found*100:.1f}% of {both_found} samples where both found issues)")
        print(f"Partial agreement (some CWEs match): {partial} ({partial/both_found*100:.1f}% of {both_found} samples where both found issues)")
        print(f"No agreement: {none} ({none/both_found*100:.1f}% of {both_found} samples where both found issues)")


def print_llm_stats(stats, total_samples):
    """Print statistics for LLM models"""
    print("\n\n" + "=" * 80)
    print("LLM MODELS")
    print("=" * 80)
    
    for model, model_stats in stats['models'].items():
        found = model_stats['found']
        matched = model_stats['matched_true']
        
        print(f"\n{model}:")
        print(f"  Found issues for {found} samples out of {total_samples} samples")
        print(f"  Exactly matched true label {matched} times ({matched/total_samples*100:.1f}% of all {total_samples} samples)")
    
    print(f"\n{'='*80}")
    print("AGREEMENT AMONG ALL LLMs")
    print("="*80)
    
    all_found = stats['all_agreement']['all_found']
    full = stats['all_agreement']['full']
    partial = stats['all_agreement']['partial']
    none = stats['all_agreement']['none']
    
    at_least_two = full + partial + none
    
    print(f"\nAt least 2 LLMs found issues: {at_least_two} samples")
    print(f"All LLMs found issues: {all_found} samples")
    
    if at_least_two > 0:
        print(f"\nFull agreement (all LLMs agree): {full} ({full/at_least_two*100:.1f}% of {at_least_two} samples)")
        print(f"Partial agreement (some LLMs agree): {partial} ({partial/at_least_two*100:.1f}% of {at_least_two} samples)")
        print(f"No agreement: {none} ({none/at_least_two*100:.1f}% of {at_least_two} samples)")


if __name__ == "__main__":
    # Total samples in dataset
    TOTAL_SAMPLES = 121
    
    # File paths
    static_tool_path = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/"
                        "exp_dir_SecurityEval/"
                        "SecurityEval_consolidated_evaluation_results.json")
    llm_data_path = ("/home/s448780/workspace_hcc4/SYNKRASIS/services/"
                     "CodeSecurity/exp_dir_SecurityEval/"
                     "SecurityEval_qwen2_5_coder_32b_mistral_latest_qwen2_5_coder_latest_llama3_1_latest.json")
    mapping_path = "/home/s448780/workspace_hcc4/SYNKRASIS/services/CodeSecurity/cwe_analysis/cwe_relationships.json"
    
    # Load CWE relationship mapping
    with open(mapping_path, 'r') as f:
        cwe_mapping = json.load(f)
    
    # Analyse static tools (CodeQL & Semgrep)
    print("\nAnalysing Static Analysis Tools...")
    with open(static_tool_path, 'r') as f:
        static_data = json.load(f)
    
    static_stats = analyse_static_tools(static_data, cwe_mapping, TOTAL_SAMPLES)
    print_static_tool_stats(static_stats, TOTAL_SAMPLES)
    
    # Analyse LLMs
    print("\n\nAnalysing LLM Models...")
    with open(llm_data_path, 'r') as f:
        llm_data = json.load(f)
    
    llm_stats = analyse_llms(llm_data, cwe_mapping, TOTAL_SAMPLES)
    print_llm_stats(llm_stats, TOTAL_SAMPLES)