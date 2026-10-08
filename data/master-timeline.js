/*
  Master timeline items, shared by roadmap.html and todo.html.
  Planned dates here are the defaults; the team's edits (planned and actual dates) live in the
  shared database as 'master' records and are layered on top of these.
  kind: bar (start+end month), ms (milestone, one month), gate (decision point, one month).
  derived: [parentId, fromFraction, toFraction] = a slice of another bar, computed, not editable.
*/
window.MASTER_R=[
 {"lane":"Money stages","id":"s0","label":"S0 Foundation","kind":"bar","ps":"2026-09","pe":"2027-06","col":"#ff2052","dash":false,"derived":null},
 {"lane":"Money stages","id":"s1","label":"S1 Pilot and launch prep","kind":"bar","ps":"2027-07","pe":"2027-12","col":"#ff2052","dash":false,"derived":null},
 {"lane":"Money stages","id":"launch","label":"Launch: Basic + Free live (M1)","kind":"ms","ps":"2028-01","pe":null,"col":"#ff2052","dash":false,"derived":null},
 {"lane":"Money stages","id":"s2","label":"S2 Launch year","kind":"bar","ps":"2028-01","pe":"2028-12","col":"#f06cb4","dash":true,"derived":null},
 {"lane":"Money stages","id":"g1","label":"Gate 3.5 + 3.6: ops and demand","kind":"gate","ps":"2028-12","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Money stages","id":"s3a","label":"S3a Moderate + Brain (batch)","kind":"bar","ps":"2029-01","pe":"2029-12","col":"#a78bfa","dash":true,"derived":null},
 {"lane":"Money stages","id":"g2","label":"Gate before Ultimate","kind":"gate","ps":"2029-06","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Money stages","id":"s3b","label":"S3b Ultimate + Brain (real time)","kind":"bar","ps":"2029-07","pe":"2030-12","col":"#a78bfa","dash":true,"derived":null},
 {"lane":"Funding and people","id":"chk","label":"Checkpoint: is BD funding converting?","kind":"gate","ps":"2026-12","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Funding and people","id":"seed","label":"Seed Fund application","kind":"ms","ps":"2027-04","pe":null,"col":"#ff2052","dash":false,"derived":null},
 {"lane":"Funding and people","id":"caab","label":"CAA application (branch B)","kind":"ms","ps":"2027-07","pe":null,"col":"#ff2052","dash":false,"derived":null},
 {"lane":"Funding and people","id":"caaa","label":"CAA application (branch A)","kind":"ms","ps":"2028-07","pe":null,"col":"#f06cb4","dash":false,"derived":null},
 {"lane":"Funding and people","id":"h7","label":"Plan B hire: junior (M7)","kind":"ms","ps":"2028-07","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Funding and people","id":"h13","label":"Plan B: mid engineer + growth (M13)","kind":"ms","ps":"2029-01","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Funding and people","id":"h19","label":"Plan B: DevOps + support (M19)","kind":"ms","ps":"2029-07","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Funding and people","id":"h25","label":"Plan B: mid #2 + office (M25)","kind":"ms","ps":"2030-01","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Technical track","id":"ta","label":"Tech-A: instrumentation and baseline","kind":"bar","ps":"2026-10","pe":"2027-04","col":"#34d399","dash":false,"derived":null},
 {"lane":"Technical track","id":"tb","label":"Tech-B: harden Basic","kind":"bar","ps":"2027-03","pe":"2028-12","col":"#34d399","dash":false,"derived":null},
 {"lane":"Technical track","id":"td","label":"Tech-D: Brain prototype (internal)","kind":"bar","ps":"2028-07","pe":"2028-12","col":"#f59e0b","dash":true,"derived":null},
 {"lane":"Technical track","id":"tc","label":"Tech-C: Moderate scaffolding","kind":"bar","ps":"2028-10","pe":"2029-01","col":"#f59e0b","dash":true,"derived":null},
 {"lane":"Technical track","id":"te","label":"Tech-E: Brain into Moderate","kind":"bar","ps":"2029-01","pe":"2029-06","col":"#f59e0b","dash":true,"derived":null},
 {"lane":"Technical track","id":"tf","label":"Tech-F: Monitor v2","kind":"bar","ps":"2029-04","pe":"2029-08","col":"#f59e0b","dash":true,"derived":null},
 {"lane":"Technical track","id":"tg","label":"Tech-G: Ultimate's Brain tier","kind":"bar","ps":"2029-07","pe":"2030-12","col":"#f59e0b","dash":true,"derived":null},
 {"lane":"Technical track","id":"th","label":"Tech-H: code-authoring (unscheduled)","kind":"bar","ps":"2030-07","pe":"2030-12","col":"#60a5fa","dash":true,"derived":null},
 {"lane":"Research (FBEBC)","id":"fb1","label":"FBEBC Stage 1: 4-week preprint","kind":"bar","ps":"2026-09","pe":"2026-10","col":"#60a5fa","dash":false,"derived":null},
 {"lane":"Research (FBEBC)","id":"fbg","label":"Gate: Basic live + ops + research budget","kind":"gate","ps":"2028-01","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Research (FBEBC)","id":"fb2","label":"FBEBC Stage 2 (MiniMe-integrated)","kind":"bar","ps":"2028-03","pe":"2028-12","col":"#60a5fa","dash":true,"derived":null},
 {"lane":"Products (your plan)","id":"dec","label":"Decide: fit and budget for MiniMake/MiniMate","kind":"gate","ps":"2026-11","pe":null,"col":"#f59e0b","dash":false,"derived":null},
 {"lane":"Products (your plan)","id":"mk","label":"MiniMake: terminal coding agent","kind":"bar","ps":"2027-01","pe":"2027-02","col":"#a78bfa","dash":false,"derived":null},
 {"lane":"Products (your plan)","id":"mt","label":"MiniMate: automation agent","kind":"bar","ps":"2027-03","pe":"2027-06","col":"#f06cb4","dash":false,"derived":null},
 {"lane":"Products (your plan)","id":"mk0","label":"   Phase 0 — Build-tab fixes and browser slimming","kind":"bar","ps":null,"pe":null,"col":"#a78bfa","dash":false,"derived":["mk",0.0,0.10828025477707007]},
 {"lane":"Products (your plan)","id":"mk1","label":"   Phase 1 — Contract and walking skeleton","kind":"bar","ps":null,"pe":null,"col":"#a78bfa","dash":false,"derived":["mk",0.10828025477707007,0.34394904458598724]},
 {"lane":"Products (your plan)","id":"mk2","label":"   Phase 2 — Core agent","kind":"bar","ps":null,"pe":null,"col":"#a78bfa","dash":false,"derived":["mk",0.34394904458598724,0.5668789808917197]},
 {"lane":"Products (your plan)","id":"mk3","label":"   Phase 3 — Safety and workflows","kind":"bar","ps":null,"pe":null,"col":"#a78bfa","dash":false,"derived":["mk",0.5668789808917197,0.8662420382165605]},
 {"lane":"Products (your plan)","id":"mk4","label":"   Phase 4 — Platform integration and beta","kind":"bar","ps":null,"pe":null,"col":"#a78bfa","dash":false,"derived":["mk",0.8662420382165605,1.0]},
 {"lane":"Products (your plan)","id":"mt0","label":"   Phase 0 — Foundations","kind":"bar","ps":null,"pe":null,"col":"#f06cb4","dash":false,"derived":["mt",0.0,0.09022556390977443]},
 {"lane":"Products (your plan)","id":"mt1","label":"   Phase 1 — First automation","kind":"bar","ps":null,"pe":null,"col":"#f06cb4","dash":false,"derived":["mt",0.09022556390977443,0.2932330827067669]},
 {"lane":"Products (your plan)","id":"mt2","label":"   Phase 2 — Safe unattended automations","kind":"bar","ps":null,"pe":null,"col":"#f06cb4","dash":false,"derived":["mt",0.2932330827067669,0.6917293233082706]},
 {"lane":"Products (your plan)","id":"mt3","label":"   Phase 3 — Memory, skills and triggers","kind":"bar","ps":null,"pe":null,"col":"#f06cb4","dash":false,"derived":["mt",0.6917293233082706,0.924812030075188]},
 {"lane":"Products (your plan)","id":"mt4","label":"   Phase 4 — Beta","kind":"bar","ps":null,"pe":null,"col":"#f06cb4","dash":false,"derived":["mt",0.924812030075188,1.0]}
];
