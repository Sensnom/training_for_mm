# Q4 analytic global-optimality proof

- p_A^D = 0.254712388980
- p_B^D = 0.040000000000
- p_E (one specified electrode, non-crossing shell) = 0.000180000000
- c_A = 0.014844025288 yuan/object
- c_B = 0.001675516082 yuan/object
- incumbent (0,57): cost = 0.095504416669 yuan, direct-X lower bound = 0.902397648016

|N_A|max N_B with cost < C(0,57)|cost/yuan|direct-X lower|necessary-event upper|
|---:|---:|---:|---:|---:|
|0|56|0.093828901|0.898330883|0.898341781|
|1|48|0.095268797|0.894962812|0.894971522|
|2|39|0.095033178|0.886961628|0.886968280|
|3|30|0.094797558|0.878350957|0.878355684|
|4|21|0.094561939|0.869084369|0.869087377|
|5|12|0.094326319|0.859111902|0.859113481|
|6|3|0.094090700|0.848379784|0.848380328|

All seven necessary-event upper bounds are below 0.90. By monotonicity in N_B, all cheaper points beneath each frontier point are also infeasible. Since 7 A alone already costs more than 57 B, no other strictly cheaper integer point exists.