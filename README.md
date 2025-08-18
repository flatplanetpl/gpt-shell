# ChatGPT CLI FS Bridge

**Secure CLI interface for ChatGPT integration with local filesystem**

ChatGPT CLI FS Bridge is a tool that allows ChatGPT and other OpenAI language models to safely interact with your local filesystem through a controlled API. The application creates a sandboxed environment where ChatGPT can read, write, and search files while maintaining full security control.

## 🎯 Main Use Cases

- **Programming task automation** - ChatGPT can analyze code, generate files, refactor
- **Document processing** - bulk operations on text files with ChatGPT's intelligent analysis
- **Developer assistant** - interactive help with debugging and project development using ChatGPT
- **Code analysis** - searching and analyzing large codebases with ChatGPT's understanding
- **Report generation** - automatic documentation creation based on project structure using ChatGPT

## ✨ Key Features

- 🔒 **Security sandbox** - all operations limited to defined working directory
- 🚀 **6 secure filesystem tools** - list_dir, read_file, write_file, search_text and more
- 🔄 **Intelligent error handling** - automatic retry with exponential backoff for rate limits
- 📊 **Cost tracking** - token counter and real-time cost estimation
- 🎨 **Rich CLI interface** - Markdown formatting, panels, syntax highlighting
- 🔍 **Debug mode** - detailed logs with sensitive data redaction option
- 💾 **Automatic backups** - every file modification creates a backup copy

## 🚀 Quick Start

### Requirements

- Python 3.8+
- OpenAI API key
- macOS or Linux (Windows with WSL)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/gpt-shell.git
cd gpt-shell

# Automatic setup
./setup.sh

# Configure environment variables
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY

# Run
./run.sh
```

### Manual configuration

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run
python cli_assistant_fs.py
```

## ⚙️ Configuration

### Environment variables (.env)

```bash
# Required - OpenAI API Key for ChatGPT
OPENAI_API_KEY=sk-...          # Your OpenAI API key

# ChatGPT Model Selection
OPENAI_MODEL=gpt-4             # ChatGPT model (gpt-4, gpt-3.5-turbo, etc.)

# Security
WORKDIR=/path/to/safe/dir      # Working directory (default: current)
ALLOW_SHELL=0                   # Shell command execution (0=disabled)

# Limits
MAX_BYTES_PER_READ=40000       # Max bytes per file read
MAX_OUTPUT_TOKENS=1536         # Max ChatGPT response tokens
MAX_HISTORY_MSGS=16            # Max messages in ChatGPT conversation history

# Debug
DEBUG=0                        # Debug mode (0/1)
DEBUG_FORMAT=text              # Log format (text/json)
DEBUG_REDACT=0                 # Sensitive data redaction (0/1)

# OpenAI Costs (USD per 1M tokens)
OPENAI_INPUT_PRICE_PER_M=5.0   # Input token price for ChatGPT
OPENAI_OUTPUT_PRICE_PER_M=15.0 # Output token price for ChatGPT
```

### Project context for ChatGPT (clifs.context.json)

```json
{
  "instructions": "Additional instructions for ChatGPT...",
  "project_goals": "Project goals for ChatGPT to understand...",
  "constraints": "Constraints for ChatGPT operations..."
}
```

## 📚 Available Tools

| Tool | Description | Usage Example |
|------|-------------|---------------|
| `list_dir` | Lists files and directories | "Show contents of src/ directory" |
| `read_file` | Reads file (with byte limit) | "Read config.py file" |
| `read_file_range` | Reads fragment of large file | "Show lines 100-200 from log.txt" |
| `write_file` | Writes or overwrites file | "Create test.py file with code..." |
| `list_tree` | Shows directory tree | "Show project structure" |
| `search_text` | Searches for pattern in files | "Find all occurrences of 'TODO'" |

## 🔒 Security

### Protection mechanisms

- **WORKDIR Sandbox** - impossible to exit the defined directory
- **Path traversal protection** - blocks attacks like `../../../etc/passwd`
- **Disabled shell commands** - no system command execution by default
- **Read limits** - protection against memory exhaustion
- **Automatic backups** - protection against data loss
- **Ignoring sensitive directories** - `.git`, `node_modules`, keys

### Security audit

Full audit available in [AUDIT_SECURITY_2025.txt](AUDIT_SECURITY_2025.txt)

## 🐛 Debug Mode

```bash
# Debug in text format
DEBUG=1 DEBUG_FORMAT=text ./run.sh

# Debug in JSON format
DEBUG=1 DEBUG_FORMAT=json ./run.sh

# Debug with data redaction
DEBUG=1 DEBUG_REDACT=1 ./run.sh
```

## 📖 Usage Examples

### 🔍 Code Analysis and Audit

#### Finding security vulnerabilities
```
You> Search the project for potential security vulnerabilities like SQL injection or XSS

ChatGPT> Analyzing files for security issues...
Found 3 potential problems:
1. views.py:45 - Unprotected SQL query with user input
2. templates/form.html:12 - Missing user data escaping
3. api.py:89 - Missing Content-Type validation
[Detailed report with fix suggestions]
```

#### Code complexity analysis
```
You> Find the most complex functions in the project and suggest refactoring

ChatGPT> Analyzing cyclomatic complexity...
Top 3 most complex functions:
1. process_payment() - complexity: 15 (utils/payment.py:234)
2. validate_order() - complexity: 12 (models/order.py:567) 
3. calculate_discount() - complexity: 11 (services/pricing.py:89)
[Refactoring proposals for each function]
```

### 📝 Automatic Code Generation

#### Creating unit tests
```
You> Write unit tests for the UserService class in services/user.py

ChatGPT> Analyzing UserService class...
Creating tests/test_user_service.py with 15 tests covering:
- User creation
- Email validation
- Password hashing
- Error handling
[Generates complete pytest file]
```

#### Generating CRUD API
```
You> Create REST API for Product model with full CRUD

ChatGPT> Creating Product API endpoints...
Generating:
- routes/product.py - GET/POST/PUT/DELETE endpoints
- schemas/product.py - Pydantic validation
- tests/test_product_api.py - integration tests
[Creates complete API structure]
```

### 🛠️ Refactoring and Migrations

#### JavaScript to TypeScript migration
```
You> Convert all .js files in components/ directory to TypeScript

ChatGPT> Starting TypeScript migration...
Found 12 JavaScript files.
Converting:
- Button.js → Button.tsx (adding prop types)
- Modal.js → Modal.tsx (defining interfaces)
- Form.js → Form.tsx (typing event handlers)
[Automatic conversion preserving logic]
```

#### Python syntax modernization
```
You> Update Python 2 code to Python 3 throughout the project

ChatGPT> Scanning for Python 2 syntax...
Found outdated elements:
- 8x print statements → print()
- 3x .iteritems() → .items()
- 5x xrange → range
- 2x unicode() → str()
[Performs migration with backups]
```

### 📊 Project Analysis and Reporting

#### Generating documentation from code
```
You> Generate Markdown documentation for all classes in core/ module

ChatGPT> Analyzing core/ module...
Found 8 classes, 42 public methods.
Generating docs/core-api.md:
# Core Module API
## Class: DatabaseConnection
### Methods:
- connect() - Establishes database connection
- execute(query, params) - Executes SQL query
[Complete documentation with usage examples]
```

#### Dependency analysis
```
You> Check which packages in requirements.txt are unused

ChatGPT> Analyzing imports in project...
Unused packages:
- pandas==1.3.0 (no imports found)
- requests-mock==1.9.3 (only in commented code)
- python-dotenv==0.19.0 (replaced by os.environ)
Suggest removing or updating requirements.txt
```

### 🐛 Debugging and Diagnostics

#### Error log analysis
```
You> Analyze error.log and find the most common errors

ChatGPT> Analyzing error.log file (2.3MB, 15432 lines)...
Top 5 errors:
1. ConnectionTimeout (1823 occurrences) - mainly between 14:00-15:00
2. KeyError 'user_id' (456 occurrences) - endpoint /api/profile
3. ValueError invalid literal (234 occurrences) - date parsing
4. FileNotFoundError (123 occurrences) - missing config.json
5. MemoryError (45 occurrences) - during large file processing
[Solution suggestions for each error]
```

#### Finding memory leaks
```
You> Check for memory leaks in Python files

ChatGPT> Scanning code for potential leaks...
Found problematic patterns:
1. data_processor.py:78 - Unclosed file handler
2. cache_manager.py:234 - Circular reference in cache
3. worker.py:156 - Global list growing without limit
[Fix code for each case]
```

### 🔄 Task Automation

#### Bulk file renaming
```
You> Rename all test_*.py files to *_test.py in the project

ChatGPT> Searching for test_*.py files...
Found 23 files to rename:
- test_auth.py → auth_test.py
- test_database.py → database_test.py
- test_api.py → api_test.py
[Performs renaming with logging]
```

#### Code cleanup
```
You> Remove all commented code blocks and console.log from the project

ChatGPT> Scanning files for dead code...
Found:
- 67 commented code blocks
- 23 console.log calls
- 12 debugger statements
Creating backup before cleanup...
[Removes while preserving history in .backup/]
```

### 📈 Performance Optimization

#### Finding N+1 queries
```
You> Check for N+1 query problems in Django models

ChatGPT> Analyzing models and views...
Potential N+1 problems:
1. views.py:89 - Post.objects.all() without select_related('author')
2. serializers.py:45 - Iteration over comments without prefetch
3. admin.py:23 - Multiple queries in list_display
[Suggests using select_related/prefetch_related]
```

#### Import optimization
```
You> Optimize imports - remove unused and sort

ChatGPT> Analyzing imports in 45 Python files...
Removing 89 unused imports:
- 23x 'from typing import Optional' (unused)
- 15x 'import json' (unused)
- 8x 'from datetime import datetime' (duplicates)
Sorting according to PEP8 convention...
[Reorganizes imports throughout the project]
```

### 🌐 Integrations and API

#### Generating API client from OpenAPI
```
You> I have an openapi.yaml file - generate a Python client

ChatGPT> Parsing OpenAPI specification...
Found 12 endpoints, generating:
- client/api.py - main APIClient class
- client/models.py - 8 Pydantic models
- client/exceptions.py - custom exceptions
- examples/usage.py - usage examples
[Complete client with type hints]
```

#### Creating webhooks
```
You> Add webhook support for user.created and order.completed events

ChatGPT> Creating webhook system...
Generating:
- webhooks/handlers.py - event handlers
- webhooks/models.py - WebhookSubscription model
- webhooks/sender.py - async sending with retry
- webhooks/verify.py - HMAC signature verification
[Full implementation with queuing]
```

## 💪 Advantage over GitHub Copilot/Codex

### 🗂️ Access to local files and data

Unlike GitHub Copilot, which only works within the editor context, CLI FS Bridge has full access to the filesystem within the sandbox.

#### Analysis of local production logs
```
You> I have production logs in ~/logs/prod-2024-12-15.log (200MB) - find all 500 errors and create statistics

ChatGPT> Reading file ~/logs/prod-2024-12-15.log...
Analyzing 1,245,332 log lines...

Found 3,421 HTTP 500 errors:
- 67% - Database connection timeout (mainly 02:00-04:00)
- 23% - Redis cache miss during heavy load
- 8% - External API timeout (payment gateway)
- 2% - Out of memory in image processing

Generating detailed report: error_analysis_2024-12-15.md
[Creates report with time charts and recommendations]
```

#### Working with local databases
```
You> Connect to my local SQLite database in ~/data/customers.db and generate Pydantic models

ChatGPT> Connecting to ~/data/customers.db...
Found 8 tables:
- customers (15 columns)
- orders (12 columns)
- products (8 columns)
...

Generating models/database.py with Pydantic models:
[Creates complete models based on actual DB structure]
```

#### Analysis of private configurations
```
You> Check all .env files in ~/projects/ and find duplicate API keys

ChatGPT> Scanning ~/projects/ directory for .env files...
Found 12 .env files in different projects.

Duplicate API keys:
- STRIPE_KEY used in 3 projects (same key!)
- SENDGRID_KEY in 2 projects
- AWS_ACCESS_KEY in 5 projects (3 different keys)

⚠️ ALERT: Using same STRIPE_KEY in production and development!
[Generates security report with recommendations]
```

### 🔧 Custom Tools - Extending capabilities

#### Example: Adding SQL query execution tool
```python
# Add to cli_assistant_fs.py new tool:

def execute_sql(query: str, database: str) -> dict:
    """Executes SQL query on local database"""
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return {"results": results, "row_count": len(results)}

# Register in TOOLS_SPEC
```

Usage:
```
You> Find all customers who haven't placed an order in 6 months

ChatGPT> Executing SQL query on customers.db database...
SELECT c.* FROM customers c 
LEFT JOIN orders o ON c.id = o.customer_id 
WHERE o.created_at < date('now', '-6 months') 
OR o.id IS NULL

Found 342 inactive customers.
Generating:
- inactive_customers.csv - list for email campaign
- reactivation_campaign.py - script for automated campaign
[Creates files based on actual DB data]
```

#### Example: Local Docker integration
```python
# Custom tool for container management:

def docker_control(action: str, container: str) -> dict:
    """Controls local Docker containers"""
    import subprocess
    cmd = f"docker {action} {container}"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    return {"output": result.stdout.decode(), "status": result.returncode}
```

Usage:
```
You> Check logs of the failing container and fix configuration

ChatGPT> Checking Docker container status...
3 containers running, 1 stopped (api-gateway).

Reading api-gateway logs:
Error: Cannot connect to Redis at localhost:6379

Analyzing docker-compose.yml...
Problem: api-gateway container has no link to redis.

Fixing docker-compose.yml:
[Edits file adding depends_on and link to Redis]

Restarting container...
✅ Container api-gateway is working correctly!
```

#### Example: Web scraping with local cache
```python
# Custom tool with cache for web scraping:

def scrape_with_cache(url: str, selector: str) -> dict:
    """Scrapes page with local cache"""
    cache_file = f"cache/{hashlib.md5(url.encode()).hexdigest()}.html"
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            html = f.read()
        print(f"Using cache for {url}")
    else:
        response = requests.get(url)
        html = response.text
        with open(cache_file, 'w') as f:
            f.write(html)
    
    soup = BeautifulSoup(html, 'html.parser')
    return {"data": [el.text for el in soup.select(selector)]}
```

Usage:
```
You> Monitor prices of 10 products from different stores and notify about changes

ChatGPT> Scraping product prices...
- allegro.pl/laptop-dell-xps - 4899 PLN (cache miss, fetching)
- x-kom.pl/laptop-gaming - 6299 PLN (using cache)
...

Comparing with prices from last check (prices_history.json):
📉 Price drop: Dell XPS -200 PLN (-4%)
📈 Price increase: Gaming Laptop +100 PLN (+1.6%)

Updating prices_history.json
Generating report: price_changes_2024-01-15.md
[Creates detailed report with changes and trend charts]
```

### 🔄 Full Workflow Control

#### Example: Complete deployment with tests
```
You> Prepare full deployment - tests, build, secrets check, docker, backup

ChatGPT> Starting complete deployment process...

1. Checking environment:
   - Python 3.11 ✅
   - Docker 24.0.7 ✅
   - PostgreSQL 15 ✅

2. Verifying secrets in .env.production:
   - All 23 variables set ✅
   - Checking if keys differ from .env.development ✅

3. Running tests:
   - Unit tests: 156 passed ✅
   - Integration tests: 42 passed ✅
   - E2E tests: 18 passed ✅

4. Creating database backup:
   - Dump database: backup_2024_01_15_1430.sql (2.3GB) ✅

5. Building Docker image:
   - docker build -t myapp:v2.3.0 ✅
   - Size: 387MB (optimized multi-stage)

6. Checking logs from last deployment:
   - Analyzing deployment_history.log
   - Last issue: memory spike during migration
   - Adding --max-memory flag to migration

7. Generating deployment checklist:
   [Creates deployment_checklist_v2.3.0.md with 35 checkpoints]

Everything ready for deployment! Proceed? (requires confirmation)
```

## 🤝 Contributing

1. Fork the repository
2. Create a branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Contributing guidelines

- Maintain existing code style
- Add tests for new features
- Update documentation
- Pass security audit for critical changes

## 📝 License

[TO BE DETERMINED - Suggested: MIT or Apache 2.0]

## ⚠️ Disclaimers

- Tool intended for use in controlled environments
- Do not use with untrusted AI models
- Regularly backup important data
- Monitor API usage and costs

## 🙏 Acknowledgments

- OpenAI for API and language models
- Rich community for CLI formatting library
- Contributors and testers

## 📧 Contact

Questions and suggestions: damian@lobsterbrew.pl

---

**Note**: This tool is in active development. Use with caution in production environments.
