import json, re, sys, os
sys.path.insert(0, 'csara')
from api.agents.retrieval import SKILL_STOP_WORDS, SKILL_SUMMARY_STOP_WORDS

CSARA_DIR = os.path.join(os.getcwd(), 'csara')

with open(os.path.join(CSARA_DIR, 'index.json')) as f:
    index = json.load(f)
skills_config = index.get('skills', {})

queries = [
    ('gtk4_windows_portable', 'gtk4 c windows portable bundle dll deployment'),
    ('mobile_responsive_css', 'mobile responsive tailwind css grid flexbox design'),
    ('nextjs_pages_router_typescript', 'next.js pages router typescript project setup'),
    ('innovation_scoring_system', 'innovation scoring milestones creative output field influence wikidata openalex'),
]

for name, query in queries:
    print(f'\n=== {name}: "{query}" ===')
    query_words = set(re.sub(r'[^\w\s]', '', query.lower()).split()) - SKILL_STOP_WORDS
    print(f'Query words (after stop): {query_words}')
    
    for skill_name, skill_info in skills_config.items():
        score = 0
        reasons = []
        keywords = skill_info.get('trigger_keywords', [])
        
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in query_words:
                score += 2
                reasons.append(f'exact kw "{kw}" +2')
            
            if ' ' in kw_lower:
                kw_parts = set(kw_lower.split())
                if kw_parts.issubset(query_words):
                    score += 2
                    reasons.append(f'multi-word kw "{kw}" +2')
            
            for qw in query_words:
                if len(kw_lower) >= 5 and kw_lower in qw and len(kw_lower)/len(qw) > 0.5:
                    score += 1
                    reasons.append(f'substr kw "{kw}"<->"{qw}" +1')
                    break
                if len(qw) >= 5 and qw in kw_lower and len(qw)/len(kw_lower) > 0.5:
                    score += 1
                    reasons.append(f'substr kw "{qw}"<->"{kw}" +1')
                    break
        
        summary = skill_info.get('summary', '').lower()
        summary_words = set(re.sub(r'[^\w\s]', '', summary).split()) - SKILL_SUMMARY_STOP_WORDS
        overlap = query_words & summary_words
        if overlap:
            score += len(overlap) * 0.5
            reasons.append(f'summary overlap {overlap} +{len(overlap)*0.5}')
        
        if score >= 2:
            print(f'  {skill_name}: score={score} - {reasons}')

# Now debug mem_008 for jimpage query
print('\n=== jimpage_add_new_section: mem_008 debug ===')
with open(os.path.join(CSARA_DIR, 'memory', 'atoms', 'mem_008.json')) as f:
    atom = json.load(f)
print(f'Content: {atom["content"]}')
print(f'Tags: {atom.get("tags", [])}')
print(f'Source task: {atom.get("source_task", "")}')

with open(os.path.join(CSARA_DIR, 'memory', 'index', 'word_index.json')) as f:
    wi = json.load(f)
mem8_words = [k for k, v in wi.items() if 'mem_008' in v]
print(f'Words indexing mem_008: {mem8_words[:30]}...')

query_kws = ['jimpage', 'nextjs', 'framer', 'motion', 'section', 'component', 'glassmorphism', 'space', 'theme']
print(f'\nQuery keywords: {query_kws}')
from ops.search import keyword_search
results = keyword_search(query_kws)
mem8_score = results.get('mem_008')
print(f'mem_008 score in keyword_search: {mem8_score}')
top20 = sorted(results.items(), key=lambda x: x[1], reverse=True)[:20]
print(f'Top 20 results: {top20}')
