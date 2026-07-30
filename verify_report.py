import json, re, sys

text = open('research_output_v2.txt', 'r', encoding='utf-8').read()
for line in text.splitlines():
    line = line.strip()
    if line.startswith('data: '):
        try:
            event = json.loads(line[6:])
            if event.get('node') == 'end':
                report = event.get('report','')
                metrics = event.get('metrics',{})
                qual = metrics.get('quality',{})
                sn_count = report.count('Source Notes')
                print('Report length: ' + str(len(report)) + ' chars')
                print('Source Notes count in report: ' + str(sn_count))
                print('Quality overall: ' + str(qual.get('overall','N/A')))
                scores = qual.get('scores',{})
                print('Relevance: ' + str(scores.get('relevance','?')))
                print('Depth: ' + str(scores.get('depth','?')))
                print('Novelty: ' + str(scores.get('novelty','?')))
                print('Coherence: ' + str(scores.get('coherence','?')))
                print('Citation Accuracy: ' + str(scores.get('citation_accuracy','?')))
                
                # Check for repeated content
                sections = re.split(r'\n## ', report)
                print('\nSection headings:')
                for s in sections:
                    heading_end = s.find('\n')
                    h = s[:heading_end] if heading_end > 0 else s[:50]
                    print('  - ' + h)
                    
                break
        except:
            pass
print('VERIFICATION DONE')
