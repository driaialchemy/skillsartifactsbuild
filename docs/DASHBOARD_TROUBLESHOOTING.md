# Dashboard Troubleshooting Guide

## Common Issues & Solutions

### Issue: "No pipeline runs found"

**Symptom**: Home page shows warning "No pipeline runs found"

**Cause**: No metadata in `data/traces/trace_index.json`

**Solution**:
```bash
# Run the pipeline to generate metadata
python scripts/run_pipeline.py --type baseline

# Verify trace index was created
ls data/traces/trace_index.json

# Launch dashboard
streamlit run app/Home.py
```

---

### Issue: "No calibration report found"

**Symptom**: Calibration Dashboard shows warning "No calibration report found for run: {run_id}"

**Cause**: Pipeline didn't complete stage 6 (calibrate_system)

**Solution**:
```bash
# Check if calibration report exists
ls data/calibration_report.json

# If missing, run full pipeline
python scripts/run_pipeline.py --type baseline

# Verify stage 6 completed
ls data/runs/{run_id}/stage_06_calibrate_system.json
```

---

### Issue: "No forecast data found"

**Symptom**: Confidence Analysis or Planner Review shows warning "No forecast data found"

**Cause**: Missing `forecasts_with_memos.json` or `forecasts_ranked.json`

**Solution**:
```bash
# Check for required files
ls data/forecasts_ranked.json
ls data/forecasts_with_memos.json

# If missing, run pipeline stages 1-4
python scripts/generate_forecasts.py
python scripts/detect_exceptions.py
python scripts/generate_memos.py
python scripts/score_and_rank.py

# Launch dashboard
streamlit run app/Home.py
```

---

### Issue: Page not loading / Blank page

**Symptom**: Dashboard page shows blank or stuck loading

**Cause**: Streamlit cache corruption or file read error

**Solution**:
```bash
# Method 1: Clear cache from UI
# Click "⋮" menu (top right) → "Clear cache" → "Rerun"

# Method 2: Restart Streamlit
# Press Ctrl+C in terminal
streamlit run app/Home.py

# Method 3: Delete cache directory
rm -rf ~/.streamlit/cache

# Method 4: Check for file corruption
python scripts/validate_pipeline_data.py
```

---

### Issue: Charts not rendering

**Symptom**: Empty space where charts should be

**Cause**: Missing or malformed data, pandas version issue

**Solution**:
```bash
# Check pandas version (should be 3.x or 2.x)
python -c "import pandas as pd; print(pd.__version__)"

# Verify data files are valid JSON
python -c "import json; print(json.load(open('data/forecasts_with_memos.json'))[:1])"

# Check Streamlit version
streamlit version

# Update dependencies if needed
pip install --upgrade streamlit pandas
```

---

### Issue: "ModuleNotFoundError: No module named 'streamlit'"

**Symptom**: Error when running `streamlit run app/Home.py`

**Cause**: Streamlit not installed

**Solution**:
```bash
# Install Streamlit
pip install streamlit

# Verify installation
streamlit version

# Launch dashboard
streamlit run app/Home.py
```

---

### Issue: "ModuleNotFoundError: No module named 'pandas'"

**Symptom**: Error when loading pages

**Cause**: Pandas not installed

**Solution**:
```bash
# Install pandas
pip install pandas

# Verify installation
python -c "import pandas; print(pandas.__version__)"

# Launch dashboard
streamlit run app/Home.py
```

---

### Issue: Slow page loading (>5 seconds)

**Symptom**: Pages take a long time to load

**Cause**: Large dataset, cache not working, or file I/O overhead

**Solution**:
```bash
# Check dataset size
wc -l data/forecasts_ranked.json

# If >10,000 lines, consider pagination in code

# Verify caching is working
# Look for "[2m⚙️ Cached function...[22m" in logs

# Clear old cache and restart
rm -rf ~/.streamlit/cache
streamlit run app/Home.py

# Check disk I/O
# Windows: Use Task Manager → Performance → Disk
# Linux: iostat -x 1
```

---

### Issue: "Permission denied" when exporting files

**Symptom**: Error when clicking export buttons

**Cause**: Insufficient file write permissions

**Solution**:
```bash
# Check file permissions
ls -la data/planner_feedback_export.json

# Fix permissions (Linux/Mac)
chmod 644 data/*.json

# Fix permissions (Windows)
# Right-click file → Properties → Security → Edit permissions

# Verify write access
echo "test" > data/test.txt && rm data/test.txt
```

---

### Issue: Run selector shows old runs only

**Symptom**: Recently completed runs not appearing in dropdown

**Cause**: Streamlit cache not invalidated

**Solution**:
```bash
# Method 1: Clear cache from UI
# Click "⋮" → "Clear cache" → "Rerun"

# Method 2: Modify trace_index.json to trigger reload
touch data/traces/trace_index.json

# Method 3: Hard refresh in browser
# Press Ctrl+Shift+R (or Cmd+Shift+R on Mac)

# Method 4: Restart Streamlit
# Ctrl+C then streamlit run app/Home.py
```

---

### Issue: Confidence Analysis shows "None" values

**Symptom**: Metrics display "None" or "NaN"

**Cause**: Missing fields in forecast data (e.g., `decision_confidence`)

**Cause**: Pipeline didn't complete stage 3 (generate_memos)

**Solution**:
```bash
# Check if stage 3 completed
ls data/runs/{run_id}/stage_03_generate_memos.json

# Verify forecasts_with_memos.json has decision_confidence
python -c "import json; print(json.load(open('data/forecasts_with_memos.json'))[0].get('decision_confidence'))"

# If missing, re-run stage 3
python scripts/generate_memos.py

# Refresh dashboard
```

---

### Issue: "Error: Invalid JSON" when viewing Raw Metadata

**Symptom**: JSON viewer shows error

**Cause**: Malformed JSON file (syntax error, incomplete write)

**Solution**:
```bash
# Validate JSON file
python -m json.tool data/runs/{run_id}/run_manifest.json

# If invalid, re-run pipeline
python scripts/run_pipeline.py --type baseline

# Check for incomplete writes (file size = 0)
ls -lh data/runs/{run_id}/run_manifest.json

# If file is empty or corrupted, delete and re-run
rm data/runs/{run_id}/*
export PIPELINE_RUN_ID={run_id}
python scripts/run_pipeline.py --type baseline
```

---

### Issue: Session state persists incorrectly

**Symptom**: Selected run or filter doesn't change when clicking buttons

**Cause**: Streamlit session state conflict

**Solution**:
```bash
# Method 1: Clear session state
# Refresh page in browser (F5)

# Method 2: Restart Streamlit
# Ctrl+C then streamlit run app/Home.py

# Method 3: Clear browser cache
# Ctrl+Shift+Delete → Clear browsing data

# Method 4: Use incognito/private window
# Ctrl+Shift+N (Chrome) or Ctrl+Shift+P (Firefox)
```

---

### Issue: Planner Review decisions not saving

**Symptom**: Decisions disappear after page refresh

**Cause**: Write permission issue or file path error

**Solution**:
```bash
# Check if decisions file exists and is writable
ls -la data/planner_decisions.json

# If missing, create empty array
echo "[]" > data/planner_decisions.json

# Verify write permissions
touch data/planner_decisions.json

# Check Streamlit logs for error messages
# Look in terminal where streamlit is running

# Try manual write test
python -c "import json; json.dump([], open('data/planner_decisions.json', 'w'))"
```

---

### Issue: "Address already in use" when starting Streamlit

**Symptom**: Error: `OSError: [Errno 98] Address already in use`

**Cause**: Another Streamlit instance is running on port 8501

**Solution**:
```bash
# Find and kill existing Streamlit process
# Linux/Mac:
lsof -ti:8501 | xargs kill -9

# Windows:
netstat -ano | findstr :8501
# Note the PID, then:
taskkill /PID {PID} /F

# Or use a different port
streamlit run app/Home.py --server.port 8502
```

---

### Issue: Dashboard opens but shows "Please wait..."

**Symptom**: Dashboard loads but never finishes

**Cause**: Infinite loop in data loading or script error

**Solution**:
```bash
# Check terminal for error messages
# Look for Python exceptions or warnings

# Try validation script first
python scripts/validate_dashboard.py

# If validation fails, check data integrity
python scripts/validate_pipeline_data.py

# Check for circular imports
python -c "import app.Home"

# Run with debug mode
streamlit run app/Home.py --logger.level=debug
```

---

### Issue: Unicode errors in summary.md

**Symptom**: Error: `'charmap' codec can't encode character`

**Cause**: Windows encoding issue with UTF-8 files

**Solution**:
```bash
# Set environment variable for UTF-8
# Windows PowerShell:
$env:PYTHONIOENCODING="utf-8"
streamlit run app/Home.py

# Windows CMD:
set PYTHONIOENCODING=utf-8
streamlit run app/Home.py

# Or add to script:
# Add to top of Home.py:
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

---

## Validation Checklist

Before opening an issue, run through this checklist:

- [ ] Streamlit is installed: `pip show streamlit`
- [ ] Pandas is installed: `pip show pandas`
- [ ] Trace index exists: `ls data/traces/trace_index.json`
- [ ] At least one run exists: `ls data/runs/`
- [ ] Validation passes: `python scripts/validate_dashboard.py`
- [ ] Data is valid: `python scripts/validate_pipeline_data.py`
- [ ] Cache is clear: Click "⋮" → "Clear cache"
- [ ] Browser is up to date
- [ ] No other Streamlit instance running on port 8501

---

## Debug Mode

Enable debug logging:

```bash
streamlit run app/Home.py --logger.level=debug
```

Check logs for:
- File read errors
- Missing keys in JSON
- Cache misses
- Python exceptions

---

## Getting Help

If issue persists:

1. **Check logs**: Terminal output where Streamlit is running
2. **Validate data**: `python scripts/validate_dashboard.py`
3. **Check documentation**: `app/README.md`
4. **Review architecture**: `docs/DASHBOARD_ARCHITECTURE.md`
5. **Inspect files manually**:
   ```bash
   ls data/traces/
   ls data/runs/
   cat data/traces/trace_index.json | python -m json.tool
   ```

---

## Emergency Reset

If all else fails, reset to clean state:

```bash
# WARNING: This deletes all run metadata and decisions

# Backup current state
cp -r data data.backup

# Clear metadata
rm -rf data/runs/*
rm data/traces/trace_index.json
rm data/planner_decisions.json

# Regenerate metadata
python scripts/run_pipeline.py --type baseline

# Launch dashboard
streamlit run app/Home.py

# If successful, delete backup
rm -rf data.backup
```

---

For more help, see:
- **User Guide**: `app/README.md`
- **Architecture**: `docs/DASHBOARD_ARCHITECTURE.md`
- **Deliverables**: `DELIVERABLES.md`
