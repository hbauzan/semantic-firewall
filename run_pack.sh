#!/bin/bash
set -e

echo "🚀 Starting packager..."
echo ""

python3 semantic_guardtrails_packager.py "$@"
exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "🎉 Pack completed successfully!"
else
    echo "💀 Pack failed with exit code $exit_code" >&2
fi

exit $exit_code
