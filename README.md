# PyLoC: LoC Counter
This is a very lighweight tool developed for personal usage to keep track of how much a project is growing overtime in terms of <strong>LoC (Lines of Code)</strong>.

<u>Comment lines and blank lines are ignored in the count.</u>

## Installation (system-wide)
Via `pip install`:
```bash
git clone https://github.com/marcoimbee/pyloc.git
cd pyloc
pip install .
```
Note that at least `Python v3.9` is required for running this tool.

## Usage
```bash
pyloc <path> [-e EXT1 EXT2 ...] [-g]
```
- `<path>`: required path to target directory
- `-e, --extensions EXT1 EXT2 ...`: space-separated list of file extensions to include (e.g., `py .java. cpp`). If omitted, all supported extensions are scanned.
- `-g, --use_gitignore`: exclude files and directories included in the local `.gitignore` file

### Example
```bash
pyloc my_project -e .py .java -g
```
Counts all Python and Java lines of code in the directory `my_project`, skipping files included in `my_project/.gitignore`.
