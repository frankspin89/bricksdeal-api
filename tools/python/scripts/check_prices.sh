#!/bin/bash

# Set the working directory to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the price update script
python3 update_prices.py

# Generate a timestamp for the log
timestamp=$(date +"%Y-%m-%d %H:%M:%S")

# Log the completion
echo "$timestamp - Price check completed" >> price_check.log

# Optional: Send email notification if there are price changes
# Uncomment and configure the following lines if you want email notifications
# 
# latest_report=$(ls -t output/price_changes/price_changes_*.json | head -1)
# price_changes=$(grep -c "price_changes" "$latest_report")
# 
# if [ "$price_changes" -gt 0 ]; then
#     echo "Price changes detected. See $latest_report for details." | mail -s "LEGO Price Changes Alert" your-email@example.com
# fi 