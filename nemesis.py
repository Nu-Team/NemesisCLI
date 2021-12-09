import argparse
import csv
import json
import os
import pandas
import requests

from copy import deepcopy
from ipaddress import collapse_addresses, ip_network
from itertools import zip_longest
from netaddr import IPNetwork
from time import sleep

# Terminal Colors
TC_BLUE  = '\033[38;5;39m'
TC_GREEN = '\033[38;5;47m'
TC_RED   = '\033[38;5;196m'
TC_BOLD = '\033[1m'
TC_END  = '\033[0m'

# Recursion depth control
RECURSION_DEPTH = 4

# Fields Configurations
with open("./configs/fields.json", "r", encoding="utf-8") as fields_fh:
	FIELDS_CONF = json.load(fields_fh)

# Display Configuration
with open("./configs/display.json", "r", encoding="utf-8") as display_fh:
	DISPLAY_CONF = json.load(display_fh)

# Connection Configurations
with open("./configs/connection.json", "r", encoding="utf-8") as conn_fh:
	CONNECTION_CONF = json.load(conn_fh)


# API Interfacing
def api_request(module, action, api_filter, start=None, count=None):
	sess = requests.Session()

	sess.headers.update({
			"x-api-key": CONNECTION_CONF["nu.key"],
			"nu-token" : CONNECTION_CONF["nu.token"]
		})

	body = {
		"module": f"{module}",
		"action": f"{action}",
		"filter": api_filter
	}

	if start != None:
		body["start"] = int(start)
	
	if count != None:
		body["count"] = int(count)

	resp = sess.post(url=CONNECTION_CONF["api.url"], json=body)

	return resp.status_code, resp.text

def api_refresh(action, recursion, ipv4, domains):
	sess = requests.Session()

	sess.headers.update({
			"x-api-key": CONNECTION_CONF["nu.key"],
			"nu-token" : CONNECTION_CONF["nu.token"]
		})

	body = {
		"action"   : f"{action}",
		"recursion": recursion,
		"ipv4"     : ipv4,
		"domains"  : domains
	}

	resp = sess.post(url=CONNECTION_CONF["refresh.url"], json=body)

	return resp.status_code, resp.text


# Pretty Print
def print_results(records, total, description, display):
	# Calculate Total Row Length
	row_w = 2
	for c in display["columns"]:
		row_w += c['width']+2
	row_w += len(display["columns"])


	# Build Outer Table Line
	otl = "+"
	for c in display["columns"]:
		otl = f"{otl}{'='*(c['width']+2)}"
	otl += f"{'='*(len(display['columns'])-1)}+"


	# Build Inner Table Line
	itl = "+"
	for c in display["columns"]:
		itl = f"{itl}{'-':{'-'}{'^'}{c['width']+2}}+"


	desc_val  = f"{TC_BOLD}{TC_RED}{description}{TC_END}"
	total_val = f"{TC_BOLD}{TC_BLUE}Total: {TC_END}{total}"

	total_w = 20 + len(TC_BOLD) + len(TC_BLUE) + len(TC_END)
	desc_w  = ((row_w - 20) + len(TC_BOLD) + len(TC_RED) + len(TC_END)) - 5


	# Build Header Line
	colr_w = len(TC_GREEN) + len(TC_END)
	hdrl = "|"
	for c in display["columns"]:
		h    = f"{TC_GREEN}{c['alias']}{TC_END}"
		hdrl = f"{hdrl} {h:{' '}{c['align']}{c['width']+colr_w}} |"
	

	# Print Outer Table Line
	print(f"\n{otl}")
	
	# Print Description
	print(f"| {desc_val:{' '}{'^'}{desc_w}}{total_val:{' '}{'>'}{total_w}} |")

	# Print Inner Table Line
	print(f"{itl}")

	# Print header
	print(f"{hdrl}")

	# Print Inner Table Line
	print(f"{itl}")

	# Print all records
	for r in records:
		row = "|"

		for c in display["columns"]:
			val = deepcopy(r)

			try:
				for k in c["key"]:
					val = val[k]
			except:
				val = ""
			
			if isinstance(val, str):
				val = val.strip()[:c['width']]

			if isinstance(val, list):
				val = val[0].strip()[:c['width']]

			if val == None:
				val = ""
			
			row = f"{row} {val:{' '}{c['align']}{c['width']}} |"

		# TODO: Remove hack and fix
		try:
			print(f"{row}")
		except:
			pass
	
	# Print Outer Table Line + Newline
	print(f"{otl}\n")

def print_refresh(status, message):
	'''
		{
			"job.id": "4a5cf285-24d0-45fd-aeaf-41bcf7c23ae4",
			"domains": {
				"total": 10,
				"usage": {
					"company": 150,
					"account": 150
				},
			},
			"ipv4": {
				"total": 256,
				"usage": {
					"company": 2304,
					"account": 2304
				}
			}
		}
	'''
	msg_dict = json.loads(message)

	if status == 200:
		status_str = f"{TC_BOLD}{TC_GREEN}{status}{TC_END}"
		jobid_str  = f"{TC_BOLD}{TC_BLUE}{msg_dict['job.id']}{TC_END}"

		row = f"{status_str:{' '}{'^'}{5}} - {jobid_str:{' '}{'^'}{38}} - "

		if msg_dict["domains"] != None:
			d_total_str   = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['total']}{TC_END}"
			d_company_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['usage']['company']}{TC_END}"
			d_account_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['usage']['account']}{TC_END}"

			row += f"Refreshed Domains:{d_total_str:{' '}{'^'}{5}} - "
			row += f"Domain Usage:[ Company:{d_company_str:{' '}{'^'}{9}} | Account:{d_account_str:{' '}{'^'}{9}}]"

			if msg_dict["ipv4"] != None:
				row += f" - "

		if msg_dict["ipv4"] != None:
			i_total_str   = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['total']}{TC_END}"
			i_company_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['usage']['company']}{TC_END}"
			i_account_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['usage']['account']}{TC_END}"

			row += f"Refreshed IPv4:{i_total_str:{' '}{'^'}{5}} - "
			row += f"IPv4 Usage:[ Company:{i_company_str:{' '}{'^'}{9}} | Account:{i_account_str:{' '}{'^'}{9}}]"

		print(row)

	elif status != 200:
		status_str = f"{TC_BOLD}{TC_RED}{status}{TC_END}"
		jobid_str  = f"{TC_BOLD}{TC_BLUE}{msg_dict['job.id']}{TC_END}"

		row = f"{status_str:{' '}{'^'}{5}} - {jobid_str:{' '}{'^'}{38}} - "

		if msg_dict["domains"] != None:
			if "Error" in msg_dict["domains"].keys():
				d_error_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['Error']}{TC_END}"

				row += f"Error:{d_error_str}"

			else:
				d_total_str   = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['total']}{TC_END}"
				d_company_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['usage']['company']}{TC_END}"
				d_account_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['domains']['usage']['account']}{TC_END}"

				row += f"Refreshed Domains:{d_total_str:{' '}{'^'}{5}} - "
				row += f"Domain Usage:[ Company:{d_company_str:{' '}{'^'}{9}} | Account:{d_account_str:{' '}{'^'}{9}}]"

			if msg_dict["ipv4"] != None:
				row += f" - "

		if msg_dict["ipv4"] != None:
			if "Error" in msg_dict["ipv4"].keys():
				i_error_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['Error']}{TC_END}"

				row += f"Error:{i_error_str}"

			else:
				i_total_str   = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['total']}{TC_END}"
				i_company_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['usage']['company']}{TC_END}"
				i_account_str = f"{TC_BOLD}{TC_BLUE}{msg_dict['ipv4']['usage']['account']}{TC_END}"

				row += f"Refreshed IPv4:{i_total_str:{' '}{'^'}{5}} - "
				row += f"IPv4 Usage:[ Company:{i_company_str:{' '}{'^'}{9}} | Account:{i_account_str:{' '}{'^'}{9}}]"

		print(row)


# Data Export
def save_to_csv(records, csv_file):
	with open(csv_file, "w", encoding="utf-8", newline="") as csv_fh:
		# Flatten list of dicts
		flat_results = [pandas.json_normalize(x, sep='.').to_dict(orient='records')[0] for x in records]

		# Convert any lists to newline delimited strings
		for x in flat_results:
			for k in x.keys():
				if isinstance(x[k], list):
					x[k] = "\n".join(x[k])

		columns = set()

		# Build list of column names
		for r in flat_results:
			for k in r.keys():
				columns.add(k)

		columns = list(columns)

		# Write results to CSV file
		w = csv.DictWriter(csv_fh, fieldnames=columns, dialect='excel')
		w.writeheader()
		w.writerows(flat_results)


# Action Processing
def process_list_fields(module):
	fields = FIELDS_CONF[module]

	module_str = f"{TC_BOLD}{TC_RED}{module}{TC_END}"

	print(f"\n[{TC_BOLD}{TC_BLUE}+{TC_END}] {TC_BOLD}{TC_GREEN}Available fields in the{TC_END} {module_str} {TC_BOLD}{TC_GREEN}module{TC_END}:")

	for x in fields:
		print(f"\t{x}")

def process_list_modules():
	print(f"\n[{TC_BOLD}{TC_BLUE}+{TC_END}] {TC_BOLD}{TC_GREEN}Available modules{TC_END}:")

	for m in FIELDS_CONF.keys():
		print(f"\t{m}")

def process_rules(rules_path='./rules'):
	rules_path = rules_path.rstrip('/')
	rules_path = rules_path.rstrip('\\')
	rules_path = rules_path.replace('\\', '/')
	
	for (dPath, dNames, fNames) in os.walk(rules_path):
		for f in fNames:
			if (f.startswith('.') == False)           and \
				(f.lower().endswith('.json') == True):
			
				fPath = f"{dPath}/{f}"

				with open(fPath, "r", encoding="utf-8") as fh_in:
					c = json.load(fh_in)

				# Check if rule is enabled
				if c["enabled"] != True:
					continue

				status, msg = api_request(c["module"], c["action"], c["filter"],
									   start=c["start"], count=c["count"])

				msg = json.loads(msg)

				# Only print table if there are results
				try:
					if len(msg["records"]) > 0:
						print_results(msg["records"], msg["total"], c["rule"], DISPLAY_CONF[c["module"]])
				
				except KeyError:
					print(f"{TC_BOLD}{TC_RED}ERROR{TC_END} ({f}): {json.dumps(msg, indent=4)}")

				# API limits to 1 request per second
				sleep(1)

def process_search(module, query, max_records, csv_file):
	query_filter = {
		"and": []
	}

	for param in query:
		if ':' in param:
			key   = param.split(':')[0]
			value = ":".join(param.split(':')[1:])

			if key.startswith('!+'):
				key = key[2:]
				query_filter["and"].append({
						"not": { "regex": [ f"{key}", f"{value}" ] }
					})

			elif key.startswith('!'):
				key = key[1:]
				query_filter["and"].append({
						"not": { "match": [ f"{key}", f"{value}" ] }
					})

			elif key.startswith('+'):
				key = key[1:]
				query_filter["and"].append({
						"regex": [ f"{key}", f"{value}" ]
					})

			else:
				query_filter["and"].append({
						"match": [ f"{key}", f"{value}" ]
					})

		else:
			if param.startswith('!'):
				param = param[1:]
				query_filter["and"].append({
						"not": { "exists": f"{param}" }
					})

			else:
				query_filter["and"].append({
						"exists": f"{param}"
					})

	records = []

	if max_records > 100:
		for i in range(0, (max_records//100)+1):
			status, msg = api_request(module, "search", query_filter,
								   start=i*100, count=100)

			msg = json.loads(msg)
			
			try:
				total = msg["total"]
				records[len(records):] = msg["records"]
			
			except KeyError:
				print(f"{TC_BOLD}{TC_RED}ERROR{TC_END}: {json.dumps(msg, indent=4)}")
				# print(f"{TC_BOLD}{TC_RED}DEBUG{TC_END}: {json.dumps(query_filter, indent=4)}")

			sleep(.5)

	else:
		status, msg = api_request(module, "search", query_filter,
							   start=0, count=max_records)

		msg = json.loads(msg)

		try:
			total = msg["total"]
			records[len(records):] = msg["records"]
		
		except KeyError:
			print(f"{TC_BOLD}{TC_RED}ERROR{TC_END}: {json.dumps(msg, indent=4)}")
			# print(f"{TC_BOLD}{TC_RED}DEBUG{TC_END}: {json.dumps(query_filter, indent=4)}")

	# Only print table if there are results
	if len(records) > 0:
		print_results(records, total, "Nemesis Search API", DISPLAY_CONF[module])

	# Save results to CSV file
	if csv_file != None:
		save_to_csv(records, csv_file)

def process_refresh(domains, cidrs):
	def _grouper(iterable, n, fillvalue=None):
		args = [iter([f"{x}" for x in iterable])] * n
		return zip_longest(*args, fillvalue=fillvalue)
	
	split_cidrs = []
	cidrs = collapse_addresses([ip_network(i, False) for i in cidrs if ':' not in i])

	for n in cidrs:
		net = IPNetwork(f"{n}")
		subnets = net.subnet(24)
		
		for s in subnets:
			split_cidrs.append(f"{s}")
	
	# Send domains
	for i in _grouper(domains, 10):
		i = list(filter(None.__ne__, i))

		if len(i) > 0:
			status, msg = api_refresh("refresh", RECURSION_DEPTH, [], i)
			print_refresh(status, msg)

			if int(status) == 429:
				sleep(3)
				status, msg = api_refresh("refresh", RECURSION_DEPTH, [], i)
				print_refresh(status, msg)

				if int(status) != 200:
					break

			elif int(status) != 200:
				break

			# Only allowed 1 request per second
			sleep(1)

	# Send IP Ranges
	for x in split_cidrs:
		status, msg = api_refresh("refresh", RECURSION_DEPTH, x, [])
		print_refresh(status, msg)
		
		if int(status) == 429:
			sleep(3)
			status, msg = api_refresh("refresh", RECURSION_DEPTH, [], x)
			print_refresh(status, msg)

			if int(status) != 200:
				break

		elif int(status) != 200:
			break

		# Only allowed 1 request per second
		sleep(1)


# Command-line Arguments
def get_args_dict():
	args_dict = {
		"action" : None,
		"module" : None,
		"query"  : None,
		"max"    : None,
		"domains": None,
		"domains_file": None,
		"cidrs_file"  : None,
		"csv"    : None
	}

	# Get command-line arguments
	parser = argparse.ArgumentParser()

	parser.add_argument('-a', action="store", dest="action", required=True,
		choices=["list", "rules", "search", "refresh"], help="Client action to perform")

	parser.add_argument('-m', action="store", dest="module", default=None,
		choices=["dns", "webreqs", "webcerts", "whois", "anonftp",
		"s3buckets", "credentials"], help="Nemesis module to leverage")

	parser.add_argument('-p', action="append", dest="query", default=None,
		help="Search parameters <field>:<regex>")

	parser.add_argument('-n', action="store", dest="max", default=20,
		type=int, help="Number of records to aggregate (Limit: 10000)")

	parser.add_argument('-d', action="store", dest="domains", default=None,
		help="Comma separated list of domains to refresh")

	parser.add_argument('-r', action="store", dest="cidrs", default=None,
		help="Comma separated list of CIDR ranges to refresh")

	parser.add_argument('-dL', action="store", dest="domains_file", default=None,
		help="File of line deliminated domains to refresh")

	parser.add_argument('-rL', action="store", dest="cidrs_file", default=None,
		help="File of line deliminated CIDR ranges to refresh")

	parser.add_argument('--csv', action="store", dest="csv", default=None,
		help="CSV file path to store results.")

	args = parser.parse_args()

	args_dict["action"]  = args.action
	args_dict["module"]  = args.module
	args_dict["query"]   = args.query
	args_dict["max"]     = args.max
	args_dict["domains"] = args.domains
	args_dict["cidrs"]   = args.cidrs
	args_dict["domains_file"] = args.domains_file
	args_dict["cidrs_file"]   = args.cidrs_file
	args_dict["csv"]     = args.csv

	return args_dict


# Main Driver
def main():
	args = get_args_dict()

	if args["action"] == "list":
		if args["module"] != None:
			process_list_fields(args["module"])

		else:
			process_list_modules()

	elif args["action"] == "rules":
		# Rules defined in ./rules
		process_rules()

	elif args["action"] == "search":
		assert args["module"] != None
		assert args["query"]  != None
		assert args["max"] > 0 and args["max"] <= 10000

		process_search(args["module"], args["query"], args["max"], args["csv"])

	elif args["action"] == "refresh":
		domains = []
		ranges  = []

		if args["domains"] != None:
			domains.extend([x.strip() for x in args["domains"].split(',')])

		if args["cidrs"] != None:
			ranges.extend([x.strip() for x in args["cidrs"].split(',')])

		if args["domains_file"] != None:
			with open(args["domains_file"], "r", encoding="utf-8") as dFh:
				domains.extend([x.strip() for x in dFh])

		if args["cidrs_file"] != None:
			with open(args["cidrs_file"], "r", encoding="utf-8") as dFh:
				ranges.extend([x.strip() for x in dFh])

		assert (len(domains) > 0) or (len(ranges) > 0)

		process_refresh(domains, ranges)

	else:
		print(f"Invalid Usage: Use '-h' or '--help' to see usage information.")

if __name__ == '__main__':
	main()
