from common import *

users   = get_users(sys.argv[1:])
cake    = get_cake(users[0])
factory = get_algorithm('DubinsSpanier')
print factory(users, cake).divide()
