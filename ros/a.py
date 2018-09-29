a = []
for x in range(0,3):
    y = lambda x=x : x
    a.append (y)
for b in a:
    print (b())

class A:
    def b (self):
        print ("b")

a = A ()
x = getattr(a, "b")
print (x ())

