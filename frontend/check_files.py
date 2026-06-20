import os

files = [
    'src/lib/utils.js',
    'src/components/ui/candidate-search-input.jsx',
    'src/components/ui/progressive-flux-loader.jsx',
    'src/components/ui/candidate-card-animated.jsx',
    'vite.config.js',
    'src/pages/HomePage.jsx',
    'src/pages/ResultsPage.jsx',
    'src/App.jsx',
    'src/main.jsx',
    'src/index.css',
    'tailwind.config.js',
    'postcss.config.js',
    'index.html',
    'src/api/client.js',
    'src/hooks/useSearch.js',
    'src/hooks/useWebSocket.js',
    'src/components/Header.jsx',
    'src/components/FilterPanel.jsx',
    'src/components/ExportPanel.jsx',
]

print("FILE CHECK RESULTS:")
print("-" * 50)
missing = []
for f in files:
    exists = os.path.exists(f)
    status = "OK     " if exists else "MISSING"
    print(f"  {status}  {f}")
    if not exists:
        missing.append(f)

print("-" * 50)
if missing:
    print(f"\nMISSING FILES ({len(missing)}):")
    for f in missing:
        print(f"  → {f}")
else:
    print("\nAll files exist! Run: npm run dev")