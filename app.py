import streamlit as st
import pandas as pd
from collections import deque, OrderedDict
from pprint import pprint

###############################
# FIRST/FOLLOW Functionality  #
###############################

production_list = []
t_list = OrderedDict()
nt_list = OrderedDict()

class Terminal:
    def __init__(self, symbol):
        self.symbol = symbol
    def __str__(self):
        return self.symbol

class NonTerminal:
    def __init__(self, symbol):
        self.symbol = symbol
        self.first = set()
        self.follow = set()
    def __str__(self):
        return self.symbol
    def add_first(self, symbols):
        self.first |= set(symbols)
    def add_follow(self, symbols):
        self.follow |= set(symbols)

def compute_first(symbol):
    global production_list, nt_list, t_list
    if symbol in t_list:
        return set(symbol)
    for prod in production_list:
        head, body = prod.split("->")
        if head != symbol:
            continue
        if body == "":
            nt_list[symbol].add_first(chr(1013))
            continue
        for i, Y in enumerate(body):
            if Y == symbol:
                continue
            tset = compute_first(Y)
            nt_list[symbol].add_first(tset - set(chr(1013)))
            if chr(1013) not in tset:
                break
            if i == len(body)-1:
                nt_list[symbol].add_first(chr(1013))
    return nt_list[symbol].first

def get_first(symbol):
    return compute_first(symbol)

def compute_follow(symbol):
    global production_list, nt_list, t_list
    if symbol == list(nt_list.keys())[0]:
        nt_list[symbol].add_follow('$')
    for prod in production_list:
        head, body = prod.split("->")
        for i, B in enumerate(body):
            if B != symbol:
                continue
            if i != len(body)-1:
                nt_list[symbol].add_follow(get_first(body[i+1]) - set(chr(1013)))
            if i == len(body)-1 or chr(1013) in get_first(body[i+1]):
                if B != head:
                    nt_list[symbol].add_follow(get_follow(head))

def get_follow(symbol):
    global nt_list, t_list
    if symbol in t_list:
        return None
    return nt_list[symbol].follow

def load_grammar(lines):
    global production_list, t_list, nt_list
    production_list = []
    t_list = OrderedDict()
    nt_list = OrderedDict()
    for line in lines:
        line = line.strip().replace(" ", "")
        if line.lower() in ['end', '']:
            continue
        production_list.append(line)
        head, body = line.split("->")
        if head not in nt_list:
            nt_list[head] = NonTerminal(head)
        for symbol in body:
            if not ('A' <= symbol <= 'Z'):
                if symbol not in t_list:
                    t_list[symbol] = Terminal(symbol)
            else:
                if symbol not in nt_list:
                    nt_list[symbol] = NonTerminal(symbol)

#################################
# CLR(1) Parser Construction    #
#################################

class State:
    _id = 0
    def __init__(self, closure):
        self.closure = closure
        self.no = State._id
        State._id += 1

class Item(str):
    def __new__(cls, item, lookahead=None):
        if lookahead is None:
            lookahead = []
        obj = str.__new__(cls, item)
        obj.lookahead = lookahead
        return obj
    def __str__(self):
        return super(Item, self).__str__() + ", " + "|".join(self.lookahead)

def closure(items):
    global production_list
    def exists(newitem, items):
        for i in items:
            if i == newitem and sorted(set(i.lookahead)) == sorted(set(newitem.lookahead)):
                return True
        return False

    while True:
        flag = False
        for i in list(items):
            if i.index('.') == len(i)-1:
                continue
            Y = i.split("->")[1].split('.')[1][0]
            if i.index('.')+1 < len(i)-1:
                remainder = i[i.index('.')+2:]
                first_set = set()
                for ch in remainder:
                    tset = get_first(ch)
                    first_set |= (tset - set(chr(1013)))
                    if chr(1013) not in tset:
                        break
                else:
                    first_set |= set(i.lookahead)
                lastr = list(first_set)
            else:
                lastr = i.lookahead

            for prod in production_list:
                head, body = prod.split("->")
                if head != Y:
                    continue
                newitem = Item(Y + "->." + body, lastr)
                if not exists(newitem, items):
                    items.append(newitem)
                    flag = True
        if not flag:
            break
    return items

def goto(items, symbol):
    global production_list
    initial = []
    for i in items:
        if i.index('.') == len(i)-1:
            continue
        head, body = i.split("->")
        seen, unseen = body.split(".")
        if unseen and unseen[0] == symbol:
            new_item = Item(head + "->" + seen + unseen[0] + "." + unseen[1:], i.lookahead)
            initial.append(new_item)
    return closure(initial)

def calc_states():
    def contains(states, t):
        for s in states:
            if len(s) != len(t):
                continue
            if sorted(s) == sorted(t):
                for i in range(len(s)):
                    if s[i].lookahead != t[i].lookahead:
                        break
                else:
                    return True
        return False
    global production_list, nt_list, t_list
    head, body = production_list[0].split("->")
    states = [closure([Item(head + "->." + body, ['$'])])]
    while True:
        flag = False
        for s in states:
            for symbol in list(nt_list.keys()) + list(t_list.keys()):
                t = goto(s, symbol)
                if t == [] or contains(states, t):
                    continue
                states.append(t)
                flag = True
        if not flag:
            break
    return states

def make_table(states):
    global nt_list, t_list
    def getstateno(t):
        for s in states:
            if len(s.closure) != len(t):
                continue
            if sorted(s.closure) == sorted(t):
                for i in range(len(s.closure)):
                    if s.closure[i].lookahead != t[i].lookahead:
                        break
                else:
                    return s.no
        return -1

    def getprodno(closure_item):
        prod_str = "".join(closure_item).replace(".", "")
        return production_list.index(prod_str)

    CLR_Table = OrderedDict()
    state_objs = []
    for s in states:
        state_objs.append(State(s))
    states = state_objs

    for s in states:
        CLR_Table[s.no] = OrderedDict()
        for item in s.closure:
            head, body = item.split("->")
            if body == '.':
                for term in item.lookahead:
                    CLR_Table[s.no].setdefault(term, set()).update({'r' + str(getprodno(item))})
                continue
            if item.index('.') == len(item)-1:
                if getprodno(item) == 0:
                    CLR_Table[s.no]['$'] = 'ac'
                else:
                    for term in item.lookahead:
                        CLR_Table[s.no].setdefault(term, set()).update({'r' + str(getprodno(item))})
                continue
            nextsym = body.split('.')[1]
            if nextsym == '':
                if getprodno(item) == 0:
                    CLR_Table[s.no]['$'] = 'ac'
                else:
                    for term in item.lookahead:
                        CLR_Table[s.no].setdefault(term, set()).update({'r' + str(getprodno(item))})
                continue
            nextsym = nextsym[0]
            t = goto(s.closure, nextsym)
            if t != []:
                if nextsym in t_list:
                    CLR_Table[s.no].setdefault(nextsym, set()).update({'s' + str(getstateno(t))})
                else:
                    CLR_Table[s.no][nextsym] = str(getstateno(t))
    return CLR_Table

def augment_grammar():
    global production_list, nt_list
    for i in range(ord('Z'), ord('A')-1, -1):
        if chr(i) not in nt_list:
            start_prod = production_list[0]
            production_list.insert(0, chr(i) + "->" + start_prod.split("->")[0])
            return

def generate_conflict_counts(table):
    sr = 0
    rr = 0
    for row in table.values():
        s = 0
        r = 0
        for cell in row.values():
            if cell != 'ac' and isinstance(cell, set) and len(cell) > 1:
                for val in cell:
                    if 'r' in val:
                        r += 1
                    else:
                        s += 1
                if r > 0 and s > 0:
                    sr += 1
                elif r > 0:
                    rr += 1
        # (Cells with a single action need no conflict resolution)
    return sr, rr

##########################
# Streamlit App Interface#
##########################

st.title("CLR(1) Parser Generator")

st.markdown("""
Enter your grammar productions below (one per line).  
**Format:** `A->Y1Y2...Yn` (an empty right-hand side denotes an epsilon production)  
For example:  
""")

grammar_input = st.text_area("Grammar Productions", height=200)

if st.button("Generate CLR(1) Parser"):
    if grammar_input.strip() == "":
        st.error("Please enter grammar productions.")
    else:
        # Reset globals and load the grammar
        lines = grammar_input.splitlines()
        load_grammar(lines)
        # Compute FIRST and FOLLOW for each non-terminal
        ff_data = []
        for nt in nt_list:
            compute_first(nt)
            compute_follow(nt)
            ff_data.append({
                "Non-Terminal": nt,
                "FIRST": ", ".join(sorted(nt_list[nt].first)),
                "FOLLOW": ", ".join(sorted(nt_list[nt].follow))
            })
        st.subheader("FIRST and FOLLOW")
        st.table(pd.DataFrame(ff_data))
        
        # Augment grammar and list the symbols
        augment_grammar()
        nt_keys = list(nt_list.keys())
        t_keys = list(t_list.keys()) + ['$']
        st.markdown(f"**Non-Terminals:** `{', '.join(nt_keys)}`")
        st.markdown(f"**Terminals:** `{', '.join(t_keys)}`")
        
        # Compute LR(0) items (states)
        State._id = 0  # Reset state numbering
        states = calc_states()
        items_lines = []
        for idx, state in enumerate(states):
            items_lines.append(f"Item{idx}:")
            for item in state:
                items_lines.append("    " + str(item))
        st.subheader("LR(0) Items")
        st.code("\n".join(items_lines))
        
        # Generate the CLR(1) parsing table
        table = make_table(states)
        st.subheader("CLR(1) Parsing Table")
        header = nt_keys + t_keys
        # Prepare table data: rows as states, columns as symbols
        table_rows = []
        for state_no, row in table.items():
            row_dict = {"State": state_no}
            for sym in header:
                cell = row.get(sym, "")
                if isinstance(cell, set):
                    cell_val = "/".join(sorted(cell))
                else:
                    cell_val = cell
                row_dict[sym] = cell_val
            table_rows.append(row_dict)
        df_table = pd.DataFrame(table_rows).set_index("State")
        st.table(df_table)
        
        # Display conflict summary
        sr, rr = generate_conflict_counts(table)
        st.subheader("Conflict Summary")
        st.markdown(f"- **s/r conflicts:** {sr}")
        st.markdown(f"- **r/r conflicts:** {rr}")
        if sr == 0 and rr == 0:
            st.success("Given Grammar is CLR(1)")
        else:
            st.error("Given Grammar is NOT CLR(1)")
