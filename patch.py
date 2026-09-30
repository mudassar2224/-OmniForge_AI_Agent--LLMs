import pathlib

path = pathlib.Path('app.py')
text = path.read_text('utf-8')

old_run_async = """                    # Run async agent
                    import threading
                    
                    def run_async(coro):
                        res = None
                        exc = None
                        def thread_target():
                            nonlocal res, exc
                            try:
                                res = asyncio.run(coro)
                            except Exception as e:
                                exc = e
                        t = threading.Thread(target=thread_target)
                        t.start()
                        t.join()
                        if exc:
                            raise exc
                        return res

                    result = run_async(run_agent(text_prompt, files))
                    
                    # Clear session state files so they don't persist to the next turn if empty
                    st.session_state.uploaded_files = []
                    # Extract results
                    final_answer = result.get("final_answer", "I couldn't process that request.")
                    sources = result.get("sources", [])
                    events = result.get("activity_events", [])
                    code_artifacts = result.get("code_artifacts", [])
                    media_artifacts = result.get("media_artifacts", [])
                    
                    # Update activity events display
                    if events:
                        for evt in events:
                            msg = evt.get("message", "")
                            evt_status = evt.get("status", "")
                            icon = "✅" if evt_status == "complete" else "❌" if evt_status == "failed" else "🔄"
                            st.write(f"{icon} {msg}")"""

new_run_async = """                    # Run async agent with live event streaming
                    import threading
                    import queue
                    import time
                    from omniforge.graph.events import register_global_listener, clear_global_listeners
                    
                    event_queue = queue.Queue()
                    def on_event(event):
                        event_queue.put(event)
                    
                    clear_global_listeners()
                    register_global_listener(on_event)
                    
                    def run_async(coro):
                        res = None
                        exc = None
                        def thread_target():
                            nonlocal res, exc
                            try:
                                res = asyncio.run(coro)
                            except Exception as e:
                                exc = e
                        t = threading.Thread(target=thread_target)
                        t.start()
                        
                        while t.is_alive():
                            while not event_queue.empty():
                                evt = event_queue.get()
                                msg = evt.get("message", "")
                                evt_status = evt.get("status", "")
                                icon = "✅" if evt_status == "complete" else "❌" if evt_status == "failed" else "🔄"
                                st.write(f"{icon} {msg}")
                            time.sleep(0.1)
                            
                        # Drain remaining
                        while not event_queue.empty():
                            evt = event_queue.get()
                            msg = evt.get("message", "")
                            evt_status = evt.get("status", "")
                            icon = "✅" if evt_status == "complete" else "❌" if evt_status == "failed" else "🔄"
                            st.write(f"{icon} {msg}")
                            
                        if exc:
                            raise exc
                        return res

                    result = run_async(run_agent(text_prompt, files))
                    clear_global_listeners()
                    
                    # Clear session state files so they don't persist to the next turn if empty
                    st.session_state.uploaded_files = []
                    # Extract results
                    final_answer = result.get("final_answer", "I couldn't process that request.")
                    sources = result.get("sources", [])
                    events = result.get("activity_events", [])
                    code_artifacts = result.get("code_artifacts", [])
                    media_artifacts = result.get("media_artifacts", [])"""

text = text.replace(old_run_async, new_run_async)
path.write_text(text, 'utf-8')
print('Patched app.py for live updates.')
