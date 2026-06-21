import sqlite3, json

conn = sqlite3.connect('oneplug_fallback.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute('SELECT * FROM audio_files ORDER BY created_at DESC LIMIT 1')
af = cur.fetchone()
print('=== LATEST AUDIO FILE ===')
print('  id        :', af['id'])
print('  filename  :', af['filename'])
print('  status    :', af['status'])
print('  created_at:', af['created_at'])
print('  file_path :', af['file_path'])

cur.execute('SELECT * FROM transcripts WHERE audio_file_id=? ORDER BY created_at DESC LIMIT 1', (af['id'],))
tr = cur.fetchone()
if tr:
    print()
    print('=== WHISPER RAW OUTPUT ===')
    print('  language   :', tr['language'])
    print('  duration   :', tr['duration'])
    print('  words_count:', tr['words_count'])
    print('  text       :', tr['text'])
    print()
    print('=== GEMINI ANALYSIS ===')
    analysis = json.loads(tr['analysis']) if tr['analysis'] else {}
    for k, v in analysis.items():
        print(' ', k, ':', v)
    print()
    print('=== SEGMENTS ===')
    segs = json.loads(tr['segments']) if tr['segments'] else []
    for s in segs:
        nsp = s.get('no_speech_prob', '?')
        logp = s.get('avg_logprob', '?')
        text = s.get('text', '')[:120]
        print(f"  [{s.get('start',0):.1f}s-{s.get('end',0):.1f}s] nsp={nsp} logp={logp}")
        print('   ', repr(text))
else:
    print('No transcript found.')

conn.close()
