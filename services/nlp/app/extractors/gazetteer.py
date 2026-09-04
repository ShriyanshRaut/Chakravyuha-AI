INDIAN_GIVEN_NAMES = ['Rakesh', 'Ramesh', 'Suresh', 'Mahesh', 'Dinesh', 'Rajesh', 'Naresh', 'Imran', 'Salman', 'Rehan', 'Farhan', 'Arif', 'Aslam', 'Javed', 'Sohail', 'Anirban', 'Subhankar', 'Sourav', 'Sandip', 'Debashish', 'Arindam', 'Tapan', 'Pappu', 'Bablu', 'Chotu', 'Guddu', 'Munna', 'Raju', 'Kallu', 'Amit', 'Ajay', 'Vijay', 'Sanjay', 'Rohit', 'Rahul', 'Vikram', 'Karan', 'Priya', 'Anita', 'Sunita', 'Kavita', 'Rekha', 'Shabana', 'Nasreen', 'Bikash', 'Prasenjit', 'Shyamal', 'Nitai', 'Gopal', 'Haran']
INDIAN_SURNAMES = ['Yadav', 'Sharma', 'Verma', 'Gupta', 'Singh', 'Kumar', 'Mishra', 'Tiwari', 'Ghosh', 'Bose', 'Chatterjee', 'Banerjee', 'Mukherjee', 'Das', 'Dutta', 'Roy', 'Sen', 'Saha', 'Mondal', 'Halder', 'Pal', 'Bhowmick', 'Sheikh', 'Khan', 'Ansari', 'Qureshi', 'Mallick', 'Molla', 'Hossain', 'Mehta', 'Shah', 'Patel', 'Jain', 'Agarwal', 'Bansal']
GANG_NAMES = ['Salkia gang', 'Salkia Group', 'Metiabruz syndicate', 'Kidderpore network', 'Bowbazar module', 'Rajabazar outfit']
DEMO_ORGS = ['Mehta Traders Pvt Ltd', 'Mehta Traders', 'Sunrise Exports', 'Kolkata Metal Works', 'Star Enterprises', 'Hind Logistics']
LOCATIONS = ['Bowbazar', 'Burrabazar', 'Sealdah', 'Howrah', 'Salkia', 'Metiabruz', 'Kidderpore', 'Rajabazar', 'Park Circus', 'Behala', 'Garden Reach', 'Barrackpore', 'Dum Dum', 'Shyambazar', 'Beadon Street', 'Canning Street', 'Kolkata', 'Haldia', 'Asansol', 'Siliguri']
POLICE_STATIONS = ['Bowbazar Police Station', 'Burrabazar Police Station', 'Howrah Police Station', 'Salkia Police Station']
WEAPONS = ['country-made pistol', 'country made pistol', '7.65 mm pistol', 'desi katta', 'chopper', 'iron rod', 'sharp weapon']

def build_patterns():
    patterns = []
    for org in GANG_NAMES + DEMO_ORGS:
        patterns.append({'label': 'ORG', 'pattern': org})
    for loc in POLICE_STATIONS + LOCATIONS:
        patterns.append({'label': 'GPE', 'pattern': loc})
    for w in WEAPONS:
        patterns.append({'label': 'WEAPON', 'pattern': w})
    given = {n.lower() for n in INDIAN_GIVEN_NAMES}
    surnames = {s.lower() for s in INDIAN_SURNAMES}
    patterns.append({'label': 'PERSON', 'pattern': [{'LOWER': {'IN': sorted(given)}}, {'LOWER': {'IN': sorted(surnames)}}]})
    patterns.append({'label': 'PERSON', 'pattern': [{'LOWER': {'IN': sorted(given)}}, {'IS_TITLE': True}, {'LOWER': {'IN': sorted(surnames)}}]})
    patterns.append({'label': 'PERSON', 'pattern': [{'LOWER': {'IN': sorted(given)}}, {'IS_TITLE': True}]})
    patterns.append({'label': 'PERSON', 'pattern': [{'TEXT': {'REGEX': '^[A-Z]\\.?$'}}, {'LOWER': {'IN': sorted(surnames)}}]})
    patterns.append({'label': 'PERSON', 'pattern': [{'LOWER': {'IN': ['sri', 'shri', 'smt', 'md', 'mohd', 'mr', 'mrs', 'ms']}}, {'TEXT': '.', 'OP': '?'}, {'IS_TITLE': True}, {'IS_TITLE': True, 'OP': '?'}]})
    return patterns