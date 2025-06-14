import argparse
import pandas as pd
from tqdm import tqdm
from modules.nlp_pipeline import NLPPipeline
from modules.response_gen import ResponseGenerator, DialogueManager
from modules.utils import load_config

def run_batch_inference(input_csv, output_csv):
    """Processes a CSV for Round 1 evaluation."""
    print("--- ALIENX BATCH INFERENCE (ROUND 1) ---")
    try:
        config = load_config()
        dialogue_manager = DialogueManager(config)
        nlp_pipe = NLPPipeline()
        response_gen = ResponseGenerator(dialogue_manager)
        df = pd.read_csv(input_csv)
        if 'Questions' not in df.columns: raise ValueError("'Questions' column not in CSV.")
    except Exception as e:
        print(f"FATAL: Initialization failed: {e}")
        return

    responses = []
    print(f"Processing {len(df)} questions from '{input_csv}'...")
    for question in tqdm(df['Questions'], desc="Generating Responses"):
        dialogue_manager.clear()
        english_query = nlp_pipe.translate_to_english(str(question), 'en-IN')
        response = response_gen.generate(english_query, source_lang='en-IN')
        responses.append(response)

    df['Responses'] = responses
    try:
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"--- INFERENCE COMPLETE. Output saved to '{output_csv}' ---")
    except Exception as e:
        print(f"FATAL: Could not save output: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run inference for ALIENX.")
    parser.add_argument('--input', type=str, required=True, help="Input CSV path.")
    parser.add_argument('--output', type=str, required=True, help="Output CSV path.")
    args = parser.parse_args()
    run_batch_inference(args.input, args.output)