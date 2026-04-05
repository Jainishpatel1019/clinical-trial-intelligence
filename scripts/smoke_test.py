import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== Clinical Trial Intelligence - Smoke Test ===\n")

# Test 1: Data layer
print("1. Testing data layer...")
from src.data.schema import get_connection, initialize_schema, load_demo_data

conn = get_connection()
initialize_schema(conn)
n = load_demo_data(conn)
df = conn.execute("SELECT * FROM trials").df()
assert len(df) == 300, f"Expected 300 rows, got {len(df)}"
print(f"   ✅ Loaded {len(df)} trials from DuckDB")

# Test 2: Validation
print("2. Testing validator...")
from src.data.validator import TrialValidator

result = TrialValidator().validate(df)
print(f"   ✅ Validation: {result['passed_rules']}/{result['total_rules']} rules passed")

# Test 3: Propensity scoring
print("3. Testing propensity scorer...")
from src.causal.propensity import PropensityScorer

ps_result = PropensityScorer().fit(df)
print(
    f"   ✅ Propensity AUC-ROC: {ps_result['auc_roc']:.3f}, Overlap: {ps_result['overlap_ok']}"
)

# Test 4: HTE model
print("4. Testing causal model (takes ~15s)...")
from src.causal.hte_model import HTEModel

model = HTEModel()
fit_result = model.fit(df)
subgroup_df = model.estimate_subgroup_effects()
print(
    f"   ✅ ATE: {fit_result['ate']:+.3f} (95% CI [{fit_result['ate_lower']:+.3f}, {fit_result['ate_upper']:+.3f}])"
)
print(f"   ✅ {len(subgroup_df)} subgroup estimates computed")

# Test 5: Simulation
print("5. Testing adaptive simulation...")
from src.simulation.bandit import AdaptiveTrialSimulator

sim = AdaptiveTrialSimulator(n_arms=3, total_budget=300)
trad = sim.simulate_traditional()
adapt = sim.simulate_adaptive()
print(
    f"   ✅ Traditional winner: Arm {trad['winner']+1} | Adaptive winner: Arm {adapt['winner']+1}"
)

# Test 6: RAG indexer
print("6. Testing RAG indexer (takes ~20s for embeddings)...")
from src.rag.indexer import TrialIndexer

indexer = TrialIndexer()
indexer.build_index(df)
results = indexer.search("diabetes trials with high enrollment", k=3)
print(
    f"   ✅ Search returned {len(results)} results, top score: {results[0]['score']:.3f}"
)

# Test 7: QA chain (demo mode)
print("7. Testing QA chain...")
from src.rag.qa_chain import TrialQAChain

chain = TrialQAChain(indexer)
result = chain.ask("Which condition has the most trials?")
print(
    f"   ✅ Answer generated ({len(result['answer'])} chars), confidence: {result['confidence']}"
)

print("\n=== ALL TESTS PASSED ✅ ===")
print("Run: streamlit run app/main.py")

conn.close()
