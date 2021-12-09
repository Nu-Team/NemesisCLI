## Nemesis API Tool

Command-line tool for use with Name Unknown's Nemesis platform and API. This tool provides a rules interface for automating OSINT information detection and retrieval, for use in assessments or as part of a more robust internal security tool.


## Usage and Examples

To run rules (see "Rules" section for how to define these):

`python .\nemesis.py -a rules`

To run a query against a specific module (in this case, DNS):

`python nemesis.py -a search -m dns -p '+metadata.query.root:example.[a-z]{2,}'`

Compound queries can be created by using multiple -p flags, like so:

`python nemesis.py -a search -m dns -p '+metadata.query.root:example.[a-z]{2,}' -p '!type:NS'`

To re-submit a domain for enumeration:

`python nemesis.py -a refresh -d example.com,example2.com`


## Rules

Rules are defined in the rules folder, and enabled or disabled via the "enabled" boolean value in each rule definition. When the rules action is specified in the command, all rules that are marked as "enabled" are run. Their structure is as follows:

```JSON
{
	"enabled": boolean, determines whether a rule is run
	"rule": custom name for the rule
	"module": the module that this rule acts within
	"action": the action taken (e.g. list, rules, search, refresh)
	"start": pagination value; when in doubt, set to zero
	"count": number of results to return
	"filter": rule object for finding specific results
}
```

For examples of filter objects, please refer to the examples provided in the rules folder.


## Query Fields

A list of modules and their available fields can be found in the fields.json file in configs, or in the Name Unknown Client API Documentation: https://name-unknown.gitbook.io/name-unknown-documentation/


## API Key

You can get your API key in Nemesis by logging in, clicking "Account" and then "API Settings", and then clicking the button to generate the key and secret token. After they are generated, add them to ```configs/connection.json```.
