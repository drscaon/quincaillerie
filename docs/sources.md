# Sources of the physical values

Every value of Quincaillerie that describes the real world (a dimension and
its tolerance, a mass, a voltage, a density, a friction, a stiffness) names
its source below: a public table of a standard, a manufacturer's datasheet,
an engineering handbook, or, where none was found, an estimate with what it
rests on. Where a source gives a range, the value lies within it, and so does
every instance the generator draws around it (`tests/test_sources.py`).

The standards themselves (ISO 4017, ISO 4032, ISO 7089, ISO 965-1,
IEC 60086-2) were not consulted: the values come from the public tables and
datasheets listed, which reproduce them. A cell's nominal size is the
datasheet's maximum, as its industry standard dimensions give it; instances
are drawn down to the datasheet's minimum.

The table is written from `quincaillerie/sources.py`
(`python -m quincaillerie.sources`).

<!-- sources: begin -->
| Value | | Unit | Range the source gives | Source |
|---|---|---|---|---|
| `METRIC.M3.d` | 3 | mm |  | [iso4017](#iso4017) |
| `METRIC.M3.P` | 0.5 | mm |  | [iso4017](#iso4017) |
| `METRIC.M3.s` | 5.5 | mm | 5.32 to 5.5 | [iso4017](#iso4017) |
| `METRIC.M3.k` | 2 | mm | 1.875 to 2.125 | [iso4017](#iso4017) |
| `METRIC.M3.m` | 2.4 | mm | 2.15 to 2.4 | [iso4032](#iso4032) |
| `METRIC.M3.washer.d1` | 3.2 | mm |  | [iso7089](#iso7089) |
| `METRIC.M3.washer.d2` | 7 | mm |  | [iso7089](#iso7089) |
| `METRIC.M3.washer.h` | 0.5 | mm | 0.45 to 0.55 | [iso7089](#iso7089) |
| `TOLERANCES.M3.s_min` | 5.32 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M3.k_min` | 1.875 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M3.k_max` | 2.125 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M3.m_min` | 2.15 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M3.washer_h.min` | 0.45 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M3.washer_h.max` | 0.55 | mm |  | [iso7089](#iso7089) |
| `METRIC.M4.d` | 4 | mm |  | [iso4017](#iso4017) |
| `METRIC.M4.P` | 0.7 | mm |  | [iso4017](#iso4017) |
| `METRIC.M4.s` | 7 | mm | 6.78 to 7 | [iso4017](#iso4017) |
| `METRIC.M4.k` | 2.8 | mm | 2.675 to 2.925 | [iso4017](#iso4017) |
| `METRIC.M4.m` | 3.2 | mm | 2.9 to 3.2 | [iso4032](#iso4032) |
| `METRIC.M4.washer.d1` | 4.3 | mm |  | [iso7089](#iso7089) |
| `METRIC.M4.washer.d2` | 9 | mm |  | [iso7089](#iso7089) |
| `METRIC.M4.washer.h` | 0.8 | mm | 0.7 to 0.9 | [iso7089](#iso7089) |
| `TOLERANCES.M4.s_min` | 6.78 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M4.k_min` | 2.675 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M4.k_max` | 2.925 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M4.m_min` | 2.9 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M4.washer_h.min` | 0.7 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M4.washer_h.max` | 0.9 | mm |  | [iso7089](#iso7089) |
| `METRIC.M5.d` | 5 | mm |  | [iso4017](#iso4017) |
| `METRIC.M5.P` | 0.8 | mm |  | [iso4017](#iso4017) |
| `METRIC.M5.s` | 8 | mm | 7.78 to 8 | [iso4017](#iso4017) |
| `METRIC.M5.k` | 3.5 | mm | 3.35 to 3.65 | [iso4017](#iso4017) |
| `METRIC.M5.m` | 4.7 | mm | 4.4 to 4.7 | [iso4032](#iso4032) |
| `METRIC.M5.washer.d1` | 5.3 | mm |  | [iso7089](#iso7089) |
| `METRIC.M5.washer.d2` | 10 | mm |  | [iso7089](#iso7089) |
| `METRIC.M5.washer.h` | 1 | mm | 0.9 to 1.1 | [iso7089](#iso7089) |
| `TOLERANCES.M5.s_min` | 7.78 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M5.k_min` | 3.35 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M5.k_max` | 3.65 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M5.m_min` | 4.4 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M5.washer_h.min` | 0.9 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M5.washer_h.max` | 1.1 | mm |  | [iso7089](#iso7089) |
| `METRIC.M6.d` | 6 | mm |  | [iso4017](#iso4017) |
| `METRIC.M6.P` | 1 | mm |  | [iso4017](#iso4017) |
| `METRIC.M6.s` | 10 | mm | 9.78 to 10 | [iso4017](#iso4017) |
| `METRIC.M6.k` | 4 | mm | 3.85 to 4.15 | [iso4017](#iso4017) |
| `METRIC.M6.m` | 5.2 | mm | 4.9 to 5.2 | [iso4032](#iso4032) |
| `METRIC.M6.washer.d1` | 6.4 | mm |  | [iso7089](#iso7089) |
| `METRIC.M6.washer.d2` | 12 | mm |  | [iso7089](#iso7089) |
| `METRIC.M6.washer.h` | 1.6 | mm | 1.4 to 1.8 | [iso7089](#iso7089) |
| `TOLERANCES.M6.s_min` | 9.78 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M6.k_min` | 3.85 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M6.k_max` | 4.15 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M6.m_min` | 4.9 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M6.washer_h.min` | 1.4 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M6.washer_h.max` | 1.8 | mm |  | [iso7089](#iso7089) |
| `METRIC.M8.d` | 8 | mm |  | [iso4017](#iso4017) |
| `METRIC.M8.P` | 1.25 | mm |  | [iso4017](#iso4017) |
| `METRIC.M8.s` | 13 | mm | 12.73 to 13 | [iso4017](#iso4017) |
| `METRIC.M8.k` | 5.3 | mm | 5.15 to 5.45 | [iso4017](#iso4017) |
| `METRIC.M8.m` | 6.8 | mm | 6.44 to 6.8 | [iso4032](#iso4032) |
| `METRIC.M8.washer.d1` | 8.4 | mm |  | [iso7089](#iso7089) |
| `METRIC.M8.washer.d2` | 16 | mm |  | [iso7089](#iso7089) |
| `METRIC.M8.washer.h` | 1.6 | mm | 1.4 to 1.8 | [iso7089](#iso7089) |
| `TOLERANCES.M8.s_min` | 12.73 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M8.k_min` | 5.15 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M8.k_max` | 5.45 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M8.m_min` | 6.44 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M8.washer_h.min` | 1.4 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M8.washer_h.max` | 1.8 | mm |  | [iso7089](#iso7089) |
| `METRIC.M10.d` | 10 | mm |  | [iso4017](#iso4017) |
| `METRIC.M10.P` | 1.5 | mm |  | [iso4017](#iso4017) |
| `METRIC.M10.s` | 16 | mm | 15.73 to 16 | [iso4017](#iso4017) |
| `METRIC.M10.k` | 6.4 | mm | 6.22 to 6.58 | [iso4017](#iso4017) |
| `METRIC.M10.m` | 8.4 | mm | 8.04 to 8.4 | [iso4032](#iso4032) |
| `METRIC.M10.washer.d1` | 10.5 | mm |  | [iso7089](#iso7089) |
| `METRIC.M10.washer.d2` | 20 | mm |  | [iso7089](#iso7089) |
| `METRIC.M10.washer.h` | 2 | mm | 1.8 to 2.2 | [iso7089](#iso7089) |
| `TOLERANCES.M10.s_min` | 15.73 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M10.k_min` | 6.22 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M10.k_max` | 6.58 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M10.m_min` | 8.04 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M10.washer_h.min` | 1.8 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M10.washer_h.max` | 2.2 | mm |  | [iso7089](#iso7089) |
| `METRIC.M12.d` | 12 | mm |  | [iso4017](#iso4017) |
| `METRIC.M12.P` | 1.75 | mm |  | [iso4017](#iso4017) |
| `METRIC.M12.s` | 18 | mm | 17.73 to 18 | [iso4017](#iso4017) |
| `METRIC.M12.k` | 7.5 | mm | 7.32 to 7.68 | [iso4017](#iso4017) |
| `METRIC.M12.m` | 10.8 | mm | 10.37 to 10.8 | [iso4032](#iso4032) |
| `METRIC.M12.washer.d1` | 13 | mm |  | [iso7089](#iso7089) |
| `METRIC.M12.washer.d2` | 24 | mm |  | [iso7089](#iso7089) |
| `METRIC.M12.washer.h` | 2.5 | mm | 2.3 to 2.7 | [iso7089](#iso7089) |
| `TOLERANCES.M12.s_min` | 17.73 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M12.k_min` | 7.32 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M12.k_max` | 7.68 | mm |  | [iso4017](#iso4017) |
| `TOLERANCES.M12.m_min` | 10.37 | mm |  | [iso4032](#iso4032) |
| `TOLERANCES.M12.washer_h.min` | 2.3 | mm |  | [iso7089](#iso7089) |
| `TOLERANCES.M12.washer_h.max` | 2.7 | mm |  | [iso7089](#iso7089) |
| `UNDER_HEAD.M3.dw_min` | 4.57 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M3.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M3.c.max` | 0.4 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M3.r_min` | 0.1 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M3.da_max` | 3.6 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `UNDER_HEAD.M4.dw_min` | 5.88 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M4.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M4.c.max` | 0.4 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M4.r_min` | 0.2 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M4.da_max` | 4.7 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `UNDER_HEAD.M5.dw_min` | 6.88 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M5.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M5.c.max` | 0.5 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M5.r_min` | 0.2 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M5.da_max` | 5.7 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `UNDER_HEAD.M6.dw_min` | 8.88 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M6.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M6.c.max` | 0.5 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M6.r_min` | 0.25 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M6.da_max` | 6.8 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `UNDER_HEAD.M8.dw_min` | 11.63 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M8.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M8.c.max` | 0.6 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M8.r_min` | 0.4 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M8.da_max` | 9.2 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `UNDER_HEAD.M10.dw_min` | 14.63 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M10.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M10.c.max` | 0.6 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M10.r_min` | 0.4 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M10.da_max` | 11.2 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `UNDER_HEAD.M12.dw_min` | 16.63 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M12.c.min` | 0.15 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M12.c.max` | 0.6 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M12.r_min` | 0.6 | mm |  | [jisb1180](#jisb1180) |
| `UNDER_HEAD.M12.da_max` | 13.7 | mm |  | [iso4014_westfield](#iso4014_westfield) |
| `BOLT.M3.b` | 12 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M3.ds_min` | 2.86 | mm |  to 3 | [jisb1180](#jisb1180) |
| `BOLT.M3.lengths.20` | 20 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M3.lengths.25` | 25 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M3.lengths.30` | 30 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M4.b` | 14 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M4.ds_min` | 3.82 | mm |  to 4 | [jisb1180](#jisb1180) |
| `BOLT.M4.lengths.25` | 25 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M4.lengths.30` | 30 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M4.lengths.35` | 35 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M4.lengths.40` | 40 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.b` | 16 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.ds_min` | 4.82 | mm |  to 5 | [jisb1180](#jisb1180) |
| `BOLT.M5.lengths.25` | 25 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.lengths.30` | 30 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.lengths.35` | 35 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.lengths.40` | 40 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.lengths.45` | 45 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M5.lengths.50` | 50 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.b` | 18 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.ds_min` | 5.82 | mm |  to 6 | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.30` | 30 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.35` | 35 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.40` | 40 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.45` | 45 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.50` | 50 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.55` | 55 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M6.lengths.60` | 60 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.b` | 22 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.ds_min` | 7.78 | mm |  to 8 | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.40` | 40 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.45` | 45 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.50` | 50 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.55` | 55 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.60` | 60 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.65` | 65 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.70` | 70 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M8.lengths.80` | 80 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.b` | 26 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.ds_min` | 9.78 | mm |  to 10 | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.45` | 45 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.50` | 50 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.55` | 55 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.60` | 60 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.65` | 65 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.70` | 70 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.80` | 80 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.90` | 90 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M10.lengths.100` | 100 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.b` | 30 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.ds_min` | 11.73 | mm |  to 12 | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.50` | 50 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.55` | 55 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.60` | 60 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.65` | 65 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.70` | 70 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.80` | 80 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.90` | 90 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.100` | 100 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.110` | 110 | mm |  | [jisb1180](#jisb1180) |
| `BOLT.M12.lengths.120` | 120 | mm |  | [jisb1180](#jisb1180) |
| `LENGTHS.6` | 6 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.8` | 8 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.10` | 10 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.12` | 12 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.16` | 16 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.20` | 20 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.25` | 25 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.30` | 30 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.35` | 35 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.40` | 40 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.45` | 45 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.50` | 50 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.55` | 55 | mm |  | [iso4017](#iso4017) |
| `LENGTHS.60` | 60 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.3` | 0.2 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.6` | 0.24 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.10` | 0.29 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.16` | 0.35 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.30` | 0.42 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.50` | 0.5 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.80` | 0.6 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.120` | 0.7 | mm |  | [iso4017](#iso4017) |
| `LENGTH_TOLERANCE.150` | 0.8 | mm |  | [iso4017](#iso4017) |
| `CELLS.AAA.d` | 10.5 | mm | 9.5 to 10.5 | [e92](#e92) |
| `CELL_MIN.AAA.d_min` | 9.5 | mm |  | [e92](#e92) |
| `CELLS.AAA.L` | 44.5 | mm | 43.3 to 44.5 | [e92](#e92) |
| `CELL_MIN.AAA.L_min` | 43.3 | mm |  | [e92](#e92) |
| `CELLS.AAA.volts` | 1.5 | V |  | [e92](#e92) |
| `CELLS.AAA.mass` | 11.5 | g |  | [e92](#e92) |
| `CELLS.AAA.nub_d` | 3.8 | mm | 0 to 3.8 | [e92](#e92) |
| `CELLS.AAA.nub_h` | 0.8 | mm | 0.8 to  | [e92](#e92) |
| `CELLS.AAA.F` | 2.5 | N |  | [holder_design](#holder_design) |
| `CELLS.AAA.pre` | 4 | mm |  | [holder_design](#holder_design) |
| `CELLS.AA.d` | 14.5 | mm | 13.5 to 14.5 | [e91](#e91) |
| `CELL_MIN.AA.d_min` | 13.5 | mm |  | [e91](#e91) |
| `CELLS.AA.L` | 50.5 | mm | 49.5 to 50.5 | [e91](#e91) |
| `CELL_MIN.AA.L_min` | 49.5 | mm |  | [e91](#e91) |
| `CELLS.AA.volts` | 1.5 | V |  | [e91](#e91) |
| `CELLS.AA.mass` | 23 | g |  | [e91](#e91) |
| `CELLS.AA.nub_d` | 5.5 | mm | 0 to 5.5 | [e91](#e91) |
| `CELLS.AA.nub_h` | 1 | mm | 1 to  | [e91](#e91) |
| `CELLS.AA.F` | 3.5 | N |  | [holder_design](#holder_design) |
| `CELLS.AA.pre` | 5 | mm |  | [holder_design](#holder_design) |
| `CELLS.C.d` | 26.2 | mm | 24.9 to 26.2 | [e93](#e93) |
| `CELL_MIN.C.d_min` | 24.9 | mm |  | [e93](#e93) |
| `CELLS.C.L` | 50 | mm | 48.5 to 50 | [e93](#e93) |
| `CELL_MIN.C.L_min` | 48.5 | mm |  | [e93](#e93) |
| `CELLS.C.volts` | 1.5 | V |  | [e93](#e93) |
| `CELLS.C.mass` | 66.2 | g |  | [e93](#e93) |
| `CELLS.C.nub_d` | 7.5 | mm | 0 to 7.5 | [e93](#e93) |
| `CELLS.C.nub_h` | 1.5 | mm | 1.5 to  | [e93](#e93) |
| `CELLS.C.F` | 5 | N |  | [holder_design](#holder_design) |
| `CELLS.C.pre` | 5 | mm |  | [holder_design](#holder_design) |
| `CELLS.D.d` | 34.2 | mm | 32.3 to 34.2 | [e95](#e95) |
| `CELL_MIN.D.d_min` | 32.3 | mm |  | [e95](#e95) |
| `CELLS.D.L` | 61.5 | mm | 59.5 to 61.5 | [e95](#e95) |
| `CELL_MIN.D.L_min` | 59.5 | mm |  | [e95](#e95) |
| `CELLS.D.volts` | 1.5 | V |  | [e95](#e95) |
| `CELLS.D.mass` | 139 | g |  | [e95](#e95) |
| `CELLS.D.nub_d` | 9.5 | mm | 0 to 9.5 | [e95](#e95) |
| `CELLS.D.nub_h` | 1.5 | mm | 1.5 to  | [e95](#e95) |
| `CELLS.D.F` | 6 | N |  | [holder_design](#holder_design) |
| `CELLS.D.pre` | 6 | mm |  | [holder_design](#holder_design) |
| `CELLS.CR123A.d` | 17 | mm | 16 to 17 | [el123](#el123) |
| `CELL_MIN.CR123A.d_min` | 16 | mm |  | [el123](#el123) |
| `CELLS.CR123A.L` | 34.5 | mm | 33.5 to 34.5 | [el123](#el123) |
| `CELL_MIN.CR123A.L_min` | 33.5 | mm |  | [el123](#el123) |
| `CELLS.CR123A.volts` | 3 | V |  | [el123](#el123) |
| `CELLS.CR123A.mass` | 16.5 | g |  | [el123](#el123) |
| `CELLS.CR123A.nub_d` | 5 | mm | 0 to  | [cell_nub](#cell_nub) |
| `CELLS.CR123A.nub_h` | 1 | mm | 1 to  | [el123](#el123) |
| `CELLS.CR123A.F` | 3 | N |  | [holder_design](#holder_design) |
| `CELLS.CR123A.pre` | 4 | mm |  | [holder_design](#holder_design) |
| `CELLS.18650.d` | 18.4 | mm | 18.26 to 18.4 | [inr18650](#inr18650) |
| `CELL_MIN.18650.d_min` | 18.26 | mm |  | [inr18650](#inr18650) |
| `CELLS.18650.L` | 65 | mm | 64.7 to 65 | [inr18650](#inr18650) |
| `CELL_MIN.18650.L_min` | 64.7 | mm |  | [inr18650](#inr18650) |
| `CELLS.18650.volts` | 3.6 | V |  | [inr18650](#inr18650) |
| `CELLS.18650.mass` | 43.8 | g | 0 to 45 | [inr18650](#inr18650) |
| `CELLS.18650.nub_d` | 8 | mm | 0 to  | [cell_nub](#cell_nub) |
| `CELLS.18650.nub_h` | 0.5 | mm |  | [cell_nub](#cell_nub) |
| `CELLS.18650.F` | 5 | N |  | [holder_design](#holder_design) |
| `CELLS.18650.pre` | 5 | mm |  | [holder_design](#holder_design) |
| `CELLS.21700.d` | 21.22 | mm | 21 to 21.22 | [inr21700](#inr21700) |
| `CELL_MIN.21700.d_min` | 21 | mm |  | [inr21700_estimate](#inr21700_estimate) |
| `CELLS.21700.L` | 70.3 | mm | 69.95 to 70.3 | [inr21700](#inr21700) |
| `CELL_MIN.21700.L_min` | 69.95 | mm |  | [inr21700_estimate](#inr21700_estimate) |
| `CELLS.21700.volts` | 3.6 | V |  | [inr21700](#inr21700) |
| `CELLS.21700.mass` | 66.8 | g | 0 to 70 | [inr21700_estimate](#inr21700_estimate) |
| `CELLS.21700.nub_d` | 8.5 | mm | 0 to  | [cell_nub](#cell_nub) |
| `CELLS.21700.nub_h` | 0.5 | mm |  | [cell_nub](#cell_nub) |
| `CELLS.21700.F` | 6 | N |  | [holder_design](#holder_design) |
| `CELLS.21700.pre` | 5 | mm |  | [holder_design](#holder_design) |
| `CELLS.9V.L` | 48.5 | mm | 46.4 to 48.5 | [e522](#e522) |
| `CELL_MIN.9V.L_min` | 46.4 | mm |  | [e522](#e522) |
| `CELLS.9V.W` | 26.5 | mm | 24.5 to 26.5 | [e522](#e522) |
| `CELL_MIN.9V.W_min` | 24.5 | mm |  | [e522](#e522) |
| `CELLS.9V.T` | 17.5 | mm | 15.5 to 17.5 | [e522](#e522) |
| `CELL_MIN.9V.T_min` | 15.5 | mm |  | [e522](#e522) |
| `CELLS.9V.volts` | 9 | V |  | [e522](#e522) |
| `CELLS.9V.mass` | 45.6 | g |  | [e522](#e522) |
| `CELLS.9V.F` | 4 | N |  | [holder_design](#holder_design) |
| `CELLS.9V.pre` | 5 | mm |  | [holder_design](#holder_design) |
| `CELLS.CR2032.d` | 20 | mm | 19.7 to 20 | [cr2032](#cr2032) |
| `CELL_MIN.CR2032.d_min` | 19.7 | mm |  | [cr2032](#cr2032) |
| `CELLS.CR2032.h` | 3.2 | mm | 2.9 to 3.2 | [cr2032](#cr2032) |
| `CELL_MIN.CR2032.h_min` | 2.9 | mm |  | [cr2032](#cr2032) |
| `CELLS.CR2032.volts` | 3 | V |  | [cr2032](#cr2032) |
| `CELLS.CR2032.mass` | 3 | g |  | [cr2032](#cr2032) |
| `CELLS.CR2032.F` | 3 | N |  | [holder_design](#holder_design) |
| `CELLS.LR44.d` | 11.6 | mm | 11.3 to 11.6 | [lr44](#lr44) |
| `CELL_MIN.LR44.d_min` | 11.3 | mm |  | [lr44](#lr44) |
| `CELLS.LR44.h` | 5.4 | mm | 5 to 5.4 | [lr44](#lr44) |
| `CELL_MIN.LR44.h_min` | 5 | mm |  | [lr44](#lr44) |
| `CELLS.LR44.volts` | 1.5 | V |  | [lr44](#lr44) |
| `CELLS.LR44.mass` | 1.9 | g |  | [lr44](#lr44) |
| `CELLS.LR44.F` | 2 | N |  | [holder_design](#holder_design) |
| `variation.STEEL_DENSITY` | 7850 | kg/m³ |  | [steel](#steel) |
| `variation.DENSITY.stainless_a2` | 7930 | kg/m³ | 7480 to 8000 | [alloys](#alloys) |
| `variation.DENSITY.brass` | 8500 | kg/m³ |  | [alloys](#alloys) |
| `batteries.G_STEEL` | 79 | GPa |  | [music_wire](#music_wire) |
| `batteries.ABS_DENSITY` | 1050 | kg/m³ | 1040 to 1060 | [abs](#abs) |
| `batteries.FRICTION` | 0.3 |  |  | [plastic_friction](#plastic_friction) |
| `variation.FRICTION.zinc_clear` | 0.15 |  | 0.13 to 0.18 | [thread_friction](#thread_friction) |
| `variation.FRICTION.zinc_yellow` | 0.16 |  | 0.13 to 0.18 | [thread_friction](#thread_friction) |
| `variation.FRICTION.black_oxide` | 0.13 |  | 0.12 to 0.15 | [thread_friction](#thread_friction) |
| `variation.FRICTION.stainless_a2` | 0.2 |  |  | [thread_friction_estimate](#thread_friction_estimate) |
| `variation.FRICTION.steel_plain` | 0.17 |  |  | [thread_friction_estimate](#thread_friction_estimate) |
| `variation.FRICTION.brass` | 0.18 |  |  | [thread_friction_estimate](#thread_friction_estimate) |
| `fits: es of a g thread, constant` | 15 | µm |  | [iso965](#iso965) |
| `fits: es of a g thread, per mm of pitch` | 11 | µm |  | [iso965](#iso965) |
| `fits: Td2 grade 6, factor` | 90 | µm |  | [iso965](#iso965) |
| `fits: TD2 grade 6 / Td2 grade 6` | 1.32 |  |  | [iso965](#iso965) |
| `fits.DIAMETER_STEPS.0.99-1.4` | 1.4 | mm |  | [iso965](#iso965) |
| `fits.DIAMETER_STEPS.1.4-2.8` | 2.8 | mm |  | [iso965](#iso965) |
| `fits.DIAMETER_STEPS.2.8-5.6` | 5.6 | mm |  | [iso965](#iso965) |
| `fits.DIAMETER_STEPS.5.6-11.2` | 11.2 | mm |  | [iso965](#iso965) |
| `fits.DIAMETER_STEPS.11.2-22.4` | 22.4 | mm |  | [iso965](#iso965) |
| `fits.DIAMETER_STEPS.22.4-45.0` | 45 | mm |  | [iso965](#iso965) |

### Sources

- <a id="iso4017"></a>**iso4017** (standard table): Westfield Fasteners, ISO 4017 hex head set screw specification: table 1 (pitch, s, k, product grade A) and table 3 (length tolerances). <https://westfieldfasteners.co.uk/Standards/ScrewBolt-HexHd4017-M-THRfull.pdf>
- <a id="jisb1180"></a>**jisb1180** (standard table): Miki Pulley, hexagon bolts, excerpt from JIS B 1180 (part grade A, the ISO 4014 and ISO 4017 heads): b (reference, l up to 125 mm), ds, dw, c, r, and the nominal lengths with ls min and lg max; lg max = l - b, ls min = lg max - 5 P. <https://mikipulley.co.jp/EN/Services/Tech_data/tech09.html>
- <a id="iso4014_westfield"></a>**iso4014_westfield** (standard table): Westfield Fasteners, ISO 4014 partly threaded hex bolts: table 1 (b, c, da, dw, r). <https://www.westfieldfasteners.co.uk/Standards/ScrewBolt-HexHd4014-M-THRpart.pdf>
- <a id="tip_chamfer"></a>**tip_chamfer** (estimate): the chamfer at the tip of a screw or bolt. Estimate: ISO 4753, which sets it, is not public; the tables only say the point is chamfered (up to M4 it may be left as rolled). Drawn from the minor to the major diameter over one pitch
- <a id="fillet_shape"></a>**fillet_shape** (estimate): the shape of the fillet under the head. Estimate: the tables give its radius r (r min, and r max = (da max - d) / 2), not its curve; a straight line from the bearing face to the shank stands for the arc
- <a id="iso4032"></a>**iso4032** (standard table): Böllhoff, ISO 4032 hexagon nuts, steel 10, data sheet (m min and max, s min and max). <https://eshop-ro.boellhoff.com/out/media/pdf/ISO_4032_Stahl_10___en.pdf>
- <a id="iso7089"></a>**iso7089** (standard table): AMES, metric flat washer dimensions chart, after ISO 7089:2000 (d1, d2, h with their limits). <https://amesweb.info/Fasteners/Washers/Standard-Metric-Flat-Washer-Sizes-Dimensions-Chart.aspx>
- <a id="iso965"></a>**iso965** (handbook): Machinery's Handbook, 31st edition, ISO metric threads: fundamental deviations (es g = −(15 + 11 P) µm, EI H = 0) and the grade ratios (TD2 grade 6 = 1.32 Td2(6)); Td2 = 90 P^0.4 d^0.1 µm checked against RoyMech's M20 6g example (170 µm; the formula gives 171). <https://online.flippingbook.com/view/954046886/678/>, <https://online.flippingbook.com/view/954046886/656>, <https://roymech.org/Useful_Tables/Screws/Thread_tol.html>
- <a id="steel"></a>**steel** (handbook): Engineering ToolBox, metals and alloys densities: steel 7850 kg/m³, stainless steel 7480 to 8000. <https://www.engineeringtoolbox.com/metal-alloys-densities-d_50.html>
- <a id="alloys"></a>**alloys** (handbook): Project Materials, metal density chart: stainless steel 304 7930 kg/m³, brass 8.5 g/cm³. <https://blog.projectmaterials.com/steel/density-of-metals>, <https://blog.projectmaterials.com/category/products/steel/density-of-metals/>
- <a id="thread_friction"></a>**thread_friction** (handbook): Autodesk Inventor, friction factor in the thread of bolted connections: galvanic zinc 0.13 to 0.18 dry; black or phosphate coating 0.14 to 0.21 dry, 0.12 to 0.15 lubricated. <https://help.autodesk.com/cloudhelp/2016/ENU/Inventor-Help/files/GUID-BC1E0039-015D-4F5E-989B-7BAFAF03962B.htm>
- <a id="thread_friction_estimate"></a>**thread_friction_estimate** (estimate): dry friction of a plain steel, A2 stainless or brass thread. Estimate: no table for these was consulted: set near the plated values (0.13 to 0.18), higher for stainless steel, which galls
- <a id="music_wire"></a>**music_wire** (handbook): Master Spring, properties of spring materials: music wire ASTM A228, modulus in torsion 79.3 GPa. <https://www.masterspring.com/wp-content/uploads/2021/12/properties_of_materials.pdf>
- <a id="abs"></a>**abs** (datasheet): ABS technical data sheet: density 1.04 to 1.06 g/cm³ (ISO 1183). <https://cdn.shopify.com/s/files/1/0811/4978/8498/files/ABS_Technical_Data_Sheet.pdf>
- <a id="plastic_friction"></a>**plastic_friction** (estimate): friction of a cell's label and can on an ABS holder. Estimate: a typical dry plastic-on-metal friction; no measurement or table was consulted
- <a id="holder_design"></a>**holder_design** (estimate): a holder's contact force and its spring's compression when the cell is in. Estimate: the order of magnitude of coil-spring and leaf-clip battery contacts; no holder datasheet was consulted. The holders are Quincaillerie's own design, not a product
- <a id="cell_nub"></a>**cell_nub** (estimate): the size of a cell's + button where its datasheet gives none, or only a bound. Estimate: from photographs of the cells; within the datasheet's bounds where it gives them
- <a id="e92"></a>**e92** (datasheet): Energizer EN92 (AAA, LR03): dimensions with their limits, typical weight 11.5 g. <https://data.energizer.com/pdfs/EN92EU0126.pdf>
- <a id="e91"></a>**e91** (datasheet): Energizer EN91 (AA, LR6): dimensions with their limits; typical weight 23.0 g (E91). <https://www.farnell.com/datasheets/1820701.pdf>, <https://www.farnell.com/datasheets/1571853.pdf>
- <a id="e93"></a>**e93** (datasheet): Energizer EN93 (C, LR14): dimensions with their limits, typical weight 66.2 g. <https://assets.rs-online.com/v1698850124/Datasheets/8c7d1b3f002ec64ffb1a006ef4798df6.pdf>
- <a id="e95"></a>**e95** (datasheet): Energizer EN95 (D, LR20): dimensions with their limits; typical weight 139 g (Max Plus EP95). <https://files.batteryjunction.com/frontend/files/EN95.pdf>, <https://data.energizer.com/pdfs/ep95.pdf>
- <a id="el123"></a>**el123** (datasheet): Energizer 123 (EL123AP, CR17345): dimensions with their limits; typical weight 16.5 g. <https://www.farnell.com/datasheets/1820684.pdf>, <https://cdn.shopify.com/s/files/1/0481/9678/0183/files/123.pdf>
- <a id="inr18650"></a>**inr18650** (datasheet): Samsung SDI, introduction of INR18650-25R: diameter 18.33 ± 0.07 mm, height 64.85 ± 0.15 mm, weight 45.0 g max, 43.8 g typical. <https://www.kiwiquads.co.nz/wp-content/uploads/INR18650-25R-datasheet.pdf>
- <a id="inr21700"></a>**inr21700** (datasheet): Samsung SDI, INR21700-40T specification (abridged): height 70.30 mm max, diameter 21.22 mm max, weight 70.0 g max. <https://cdn.simpower.co.nz/wp-content/uploads/2021/09/INR21700-40T.pdf>
- <a id="inr21700_estimate"></a>**inr21700_estimate** (estimate): what the INR21700-40T datasheet does not give: its minima and its typical weight. Estimate: a dealer's figures (21.15 ± 0.15 mm, 70.15 ± 0.2 mm) for the minima; the weight retailers give (66.8 g), under the datasheet's maximum <https://www.akkuteile.de/en/samsung-inr21700-40t-4000mah-35a-li-ion-battery-3-6v-3-7v_100811_3235>
- <a id="e522"></a>**e522** (datasheet): Energizer 522 (9 V, 6LR61): dimensions with their limits; typical weight 45.6 g. <https://elcodis.com/parts/2884384/522BP.html>, <https://dtsheet.com/doc/1429949/9v-energizer-522---energizer-technical-information>, <https://media.distrelec.com/Web/Downloads/ta/_e/fr522-9V_data_e.pdf>
- <a id="cr2032"></a>**cr2032** (datasheet): Energizer CR2032: dimensions with their limits; typical weight 3.0 g. <https://data.energizer.com/pdfs/cr2032.pdf>, <https://www.radiolocman.com/datasheet/pdf.html?di=169019>
- <a id="lr44"></a>**lr44** (datasheet): GP A76 (LR44): Ø11.60 +0/−0.30 mm, 5.40 +0/−0.40 mm, average weight 1.9 g. <https://manualmachine.com/gpbatteries/a76/9622182-datasheet>

### Numbers that are not physical values

- `DEFAULT_LENGTH, DEFAULT_BOLT_LENGTH`: the length generated when none is asked for: a choice, among the standard lengths.
- `fasteners.under_head`: a part built without a sampler takes the middle of each range the tables give (bearing face, fillet, plain shank): the standards give limits only.
- `batteries.FLOOR_T`: the thickness of the holders' floor: Quincaillerie's own holder design.
- `batteries.CONTACT_OFFSET, fasteners.CONTACT_OFFSET`: the distance at which contacts are generated: a simulation setting.
- `fits.SIM_FLOOR_MM`: the least clearance generated, so that the collision pieces can slide: a simulation setting (contract, docs/physics.md).
- `fasteners.DETAIL, SEG_DEG`: mesh resolution.
- `materials.MATERIALS`: render appearance (colour, roughness), not a physical property.
- `declared.DECLARED (wear, defect, physics spreads)`: how much instances vary where no source gives a spread: declared and tested in docs/variation.md, estimates by construction.
<!-- sources: end -->
