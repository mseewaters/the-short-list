# Parking Lot

## Future ideas THAT WE WONT EVEN THINK ABOUT RIGHT NOW

## UI polish
- Better layout
- Requirements panel styling
- Chat bubbles
- Stage bar
- Loading indicator

## Future backend
- Real LLM call
- Persistent sessions
- Product discovery
- Evidence model
- Database for category intelligence
- Caching intelligence

## Notes
One note on the singleton (#7): if you write tests that need to swap LLM_PROVIDER between test cases, you'll need to reset _provider_instance = None between them (or patch get_llm_provider directly, which the existing tests already do).