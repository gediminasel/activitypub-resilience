import logging
import traceback


def main():
    domains = {}
    err = 0
    fgs = 0
    sum_fetches = 0
    with open("out/logs/lookup.perf.log") as f:
        for line in f:
            if line.startswith("F "):
                try:
                    line_p = line.split()
                    if len(line_p) != 4:
                        continue
                    fg, domain, time, act = line_p
                    time = float(time)
                    act = int(act)
                    if domain not in domains:
                        domains[domain] = 0
                    if domains[domain] > time - 1.9:
                        print("ERR", domain, domains[domain], time)
                        err += 1
                    domains[domain] = time
                    fgs += 1
                    sum_fetches += act
                except Exception as e:
                    traceback.print_exc()
                    logging.exception(e)
    print(fgs, err, sum_fetches / fgs)


if __name__ == "__main__":
    main()
