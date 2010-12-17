def checker(s):
    l = s.split("+")
    if len(l) == 10:
        return reduce(lambda x, y: int(x) + int(y), l, 0) 
    elif len(l) < 10:
        s2 = raw_input("Too few; continue...")
        return checker(s + s2)
    else:
        print "Too many; start over"
        return 0
        

def repl():
    while True:
        s = raw_input("Scores> ")
        print "Raw score: %d\n" % checker(s)
