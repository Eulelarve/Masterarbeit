from collections import defaultdict
i = defaultdict(type([]))
i['ä'].append(1)
print(i)
