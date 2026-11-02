with open("규정.txt","r",encoding="utf-8") as f:
        rules = f.read()
chunks = rules.split("[")
clean_chunks =[]
for i, chunk in enumerate(chunks):
        if chunk == '':
                continue
        clean_chunks.append("["+chunk)
        print(i,repr("["+chunk))
print(clean_chunks)