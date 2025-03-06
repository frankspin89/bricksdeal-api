# CLAUDE.md - Development Guidelines

## Build/Lint/Test Commands
- Build: `npm run build` (Turbo)
- Dev: `npm run dev` (Turbo)
- Lint: `npm run lint` (ESLint)
- Test: `npm run test` (Vitest)
- Single test: `npm run test -- -t "test name"` (API/Web)
- API specific: `cd apps/api && npm run dev:env`
- Web specific: `cd apps/web && npm run dev`
- Test coverage: `npm run test:coverage`
- Test watch: `npm run test:watch`

## Code Style Guidelines
- TypeScript: Use strong typing with interfaces and type definitions
- Naming: camelCase (variables, functions), PascalCase (components, types)
- API responses: snake_case fields, consistent JSON format with success property
- Error handling: Try/catch with structured error responses
- Components: Functional with Props interfaces, Tailwind for styling
- Tests: BDD style, descriptive names, in .test.ts(x) files
- Imports: Group by external/internal/types, alphabetical order
- File structure: Feature-based routing, schemas in dedicated files

## Python Tools
- Run extract: `cd tools/python && ./run_extract.sh`
- CLI: `bricks-deal` command after setup