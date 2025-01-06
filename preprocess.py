def parse_line(line):
    pattern = r"(\d{2}/\d{2}/\d{2}), (\d{2}:\d{2}) - (.*?): (.*)"
    match = re.match(pattern, line)

    if match:
        date = match.group(1)
        time = match.group(2)
        sender = match.group(3)
        message = match.group(4)
        return date, time, sender, message
    else:
        return None

# Extract Time
def date_time(s):
    pattern = r'^(\d+/\d+/\d+, \d+:\d+\s?[APMapm]{2}) -'
    result = re.match(pattern, s)
    #print("Line:", s)  # Debug statement
    #print("Pattern matched:", result)
    if result:
        return True
    return False

# Find Authors or Contacts
def find_author(s):
    s = s.split(":")
    if len(s)==2:
        return True
    else:
        return False
 # Finding Messages
 
def getDatapoint(line):
    splitline = line.split(' - ')
    dateTime = splitline[0]
    date, time = dateTime.split(", ")
    message = " ".join(splitline[1:])
    if find_author(message):
        splitmessage = message.split(": ")
        author = splitmessage[0]
        message = " ".join(splitmessage[1:])
    else:
        author= None
    return date, time, author, message       
    # return False



data = []
conversation ='E:/JUPYTER/WHATSAPP/WhatsApp_Chat_CBET_Champions.txt'
with open(conversation, encoding="utf-8") as fp:
    fp.readline()
    messageBuffer = []
    date, time, author = None, None, None
    while True:
        line = fp.readline()
        if not line:
            break
        line = line.strip()
        #print("Processing line:", line)
        if date_time(line):
            if len(messageBuffer) > 0:
                data.append([date, time, author, ' '.join(messageBuffer)])
                #print("Extracted data:", date, time, author, message)
            messageBuffer.clear()
            date, time, author, message = getDatapoint(line)
            #print("Extracted data:", date, time, author, message)
            messageBuffer.append(message)
        else:
            messageBuffer.append(line)
            #print("Extracted data:", messageBuffer)


df = pd.DataFrame(data, columns=["Date", 'Time','Author','Message'])
df['Date'] = pd.to_datetime(df['Date'])

data = df.dropna()
data.head(5)