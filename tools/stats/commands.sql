-- queue size per domain
SELECT domain, count(*) AS cnt FROM queue GROUP BY domain ORDER BY cnt DESC;
SELECT domain, count(*) AS cnt FROM queue WHERE state < -2 GROUP BY domain ORDER BY cnt DESC;

-- new users per day
SELECT count(*) AS Total_Count,
IIF(INSTR(json, '"published":') > 0, SUBSTRING(json, INSTR(json, '"published":')+14, 10), NULL) AS json_grp
FROM as_objects
WHERE type=2
GROUP BY json_grp
ORDER BY Total_Count DESC;

-- users on day
SELECT count(*) FROM as_objects WHERE type=2 AND json like '%"published": "2021-11-25T__:__:__Z"%';

