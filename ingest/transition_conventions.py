# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-10
# SCALE-EXEMPT: same instrument as trajectory_conventions.py, for transition
# counts: it sweeps LR/cd across LC, NT and VU and T across None, VU and EN
# precisely to show what each choice costs. Nothing imports it.
import os, psycopg2, itertools
SCALE={"LC":0,"NT":1,"VU":2,"EN":3,"CR":4}
conn=psycopg2.connect(os.environ["ARCTIC_DATABASE_URL"]); cur=conn.cursor()
cur.execute("""select s.scientific_name,a.status,a.year_published
 from arctic_v2.iucn_assessments a join arctic_v2.species s on s.id=a.species_id
 where coalesce(a.scope_code,'1')='1' and a.year_published is not null
 order by s.scientific_name,a.year_published,a.assessment_id""")
by={}
for n,st,y in cur.fetchall(): by.setdefault(n,[]).append((y,st))

# vary the two genuinely debatable mappings; K/T/NR/NA either excluded or = DD-like (excluded)
for cd in ("LC","NT","VU"):
  for t in (None,"VU","EN"):
    M={"LR/lc":"LC","LR/nt":"NT","LR/cd":cd,"V":"VU","E":"EN"}
    if t: M["T"]=t
    fn=lambda s: SCALE.get(s, SCALE.get(M.get(s)))
    imp=dec=0
    for n,rows in by.items():
        seq=[(y,fn(st)) for y,st in rows if fn(st) is not None]
        seq=[(y,r) for y,r in seq if 1982<=y<=2023]
        for i in range(1,len(seq)):
            a,b=seq[i-1][1],seq[i][1]
            if b<a: imp+=1
            elif b>a: dec+=1
        # note: species loop
    tot=imp+dec
    flag=" <== MATCHES CLAIM" if (tot,imp,dec)==(45,24,21) else ""
    print(f"LR/cd->{cd:3} T->{str(t):4}  transitions={tot:3} imp={imp:3} det={dec:3}{flag}")
print("\nCLAIM: 45 transitions (24 improvements, 21 deteriorations)")
conn.close()
