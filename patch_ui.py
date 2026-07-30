import re

with open('frontend/src/app/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

new_ui = '''
        {/* Execution Pipeline — Dual Column Design */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              ref={pipelineRef}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-8 w-full"
            >
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
                
                {/* Left Column: Live Reasoning Pipeline */}
                <div className="glass-panel p-6 sm:p-8 flex flex-col h-[500px]">
                  <div className="flex items-center justify-between mb-6 pb-4 border-b border-[var(--border)]">
                    <h3 className="text-lg font-medium text-[var(--text-1)] flex items-center gap-3">
                      <Zap className="w-5 h-5 text-[var(--brand-primary)]" />
                      Live Reasoning Pipeline
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-[var(--accent-sage)] animate-pulse" />
                      <span className="text-xs font-mono uppercase tracking-widest text-[var(--accent-sage)]">Processing</span>
                    </div>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto pr-2 space-y-3 font-mono text-xs custom-scrollbar">
                    {logs.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-[var(--text-3)]">
                        <Loader2 className="w-6 h-6 animate-spin mb-3 opacity-50" />
                        <p>Initializing neural context...</p>
                      </div>
                    ) : (
                      logs.map((log, idx) => (
                        <motion.div 
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          key={idx}
                          className="flex gap-3 text-[var(--text-2)]"
                        >
                          <span className="text-[var(--text-3)] flex-shrink-0">[{new Date().toLocaleTimeString([], {hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit'})}]</span>
                          <span className={log.startsWith('[Phase') ? 'text-[var(--brand-primary)] font-bold' : ''}>{log}</span>
                        </motion.div>
                      ))
                    )}
                    <div ref={logsEndRef} />
                  </div>
                </div>

                {/* Right Column: Live Resources */}
                <div className="glass-panel p-6 sm:p-8 flex flex-col h-[500px]">
                  <div className="flex items-center justify-between mb-6 pb-4 border-b border-[var(--border)]">
                    <h3 className="text-lg font-medium text-[var(--text-1)] flex items-center gap-3">
                      <Network className="w-5 h-5 text-[var(--accent-gold)]" />
                      Live Resources Analyzed
                    </h3>
                    <span className="text-xs font-mono bg-[var(--accent-gold)]/10 text-[var(--accent-gold)] px-2 py-1 rounded-md border border-[var(--accent-gold)]/20">
                      {sources.length} Sites
                    </span>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    {sources.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-[var(--text-3)]">
                        <Search className="w-6 h-6 mb-3 opacity-50" />
                        <p>Waiting for deep web searcher...</p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {sources.map((src, idx) => {
                          let domain = src;
                          try { domain = new URL(src).hostname; } catch(e){}
                          return (
                            <motion.a 
                              initial={{ opacity: 0, scale: 0.95 }}
                              animate={{ opacity: 1, scale: 1 }}
                              key={idx}
                              href={src}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--card)] hover:border-[var(--brand-primary)]/30 transition-all group"
                            >
                              <div className="w-6 h-6 flex-shrink-0 rounded bg-[var(--brand-primary)]/10 text-[var(--brand-primary)] flex items-center justify-center border border-[var(--brand-primary)]/20">
                                <BookOpen className="w-3 h-3" />
                              </div>
                              <div className="overflow-hidden flex-1">
                                <p className="text-xs font-medium text-[var(--text-1)] truncate group-hover:text-[var(--brand-primary)] transition-colors">{domain}</p>
                                <p className="text-[10px] text-[var(--text-3)] truncate mt-0.5">{src}</p>
                              </div>
                            </motion.a>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

              </div>
            </motion.div>
          )}
        </AnimatePresence>
'''

start_idx = content.find('        {/* Execution Pipeline — Orbital Design */}')
end_idx = content.find('        {/* Success Banner & Export */}')

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_ui + '\n' + content[end_idx:]
    with open('frontend/src/app/page.tsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced UI successfully.")
else:
    print(f"Could not find indices. Start: {start_idx}, End: {end_idx}")
