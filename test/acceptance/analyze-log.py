import re
data = open(r'C:\Users\15601\AppData\Local\Temp\pty-inter-stream.log','rb').read().decode('utf-8','replace')
ESC = chr(27); BEL = chr(7)
clean = re.sub(re.escape(ESC)+r'\][^'+re.escape(BEL)+r']*(?:'+re.escape(BEL)+'|'+re.escape(ESC)+r'\\)', '', data)
clean = re.sub(re.escape(ESC)+r'\[[0-?]*[ -/]*[@-~]', '', clean)
clean = clean.replace('\r','')
seg = clean[56000:64000]
print(seg)
print('=== AFTER 63000 ===')
seg2 = re.sub(r'[◐◓◑◒][^\n]*\n?', '', clean[63000:])
seg2 = re.sub(r'Tip:[^\n]*\n?', '', seg2)
seg2 = re.sub(r'\n{2,}', '\n', seg2)
print(seg2[:3000])
