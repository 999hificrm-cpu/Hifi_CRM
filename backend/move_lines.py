with open('app/api/v1/leads.py', 'r') as f:
    lines = f.readlines()
start = -1
end = -1
for i, l in enumerate(lines):
    if 'class BatchAssignRequest(BaseModel):' in l: start = i
    if 'def get_pre_call_context(' in l: end = i - 1

if start != -1 and end != -1:
    while end > start and lines[end].strip() == '' or '@router' in lines[end]:
        end -= 1
    end += 1 # Include the empty line or decorator? No, I will just delete until the router decorator.
    
    # Actually just search for '@router.get("/{id}/pre-call-context'
    for i, l in enumerate(lines):
        if '@router.get("/{id}/pre-call-context' in l:
            end = i
            break
            
    chunk = lines[start:end]
    del lines[start:end]
    for i, l in enumerate(lines):
        if '@router.get("/{id}", response_model=LeadOut)' in l:
            insert_idx = i - 1
            break
    lines = lines[:insert_idx] + chunk + lines[insert_idx:]
    with open('app/api/v1/leads.py', 'w') as f:
        f.writelines(lines)
    print('Moved successfully')
else:
    print(f'Not found: {start}, {end}')
