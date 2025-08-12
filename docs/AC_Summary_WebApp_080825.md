# Arctic Tracker Web Application - Technical Documentation

## Executive Summary

The Arctic Tracker is a comprehensive web application designed to support evidence-based conservation efforts for Arctic biodiversity. Developed by Magnús Smári Smárason and Tom Barry PhD at the University of Akureyri, this platform integrates multiple data sources to provide researchers, conservationists, and policymakers with advanced tools for species monitoring and analysis.

## Application Architecture

### Site Map & Navigation Graph

```
Arctic Tracker (https://magnussmari.github.io/arctic-species-2025-frontend/)
│
├── Overview (Home) [/]
│   ├── Key Metrics Dashboard
│   ├── Featured Species Carousel
│   ├── About Project Section
│   └── Data Integration Tools Overview
│
├── Species [/gallery]
│   ├── Species Gallery Grid
│   ├── Search & Filter Interface
│   │   ├── Text Search
│   │   ├── Conservation Status Filter
│   │   ├── CITES Appendix Filter
│   │   ├── Family Filter
│   │   └── Illegal Trade Filter
│   ├── Pagination System
│   └── Species Detail Pages [/species/{id}]
│       ├── Overview Tab
│       │   ├── Conservation Status Summary
│       │   ├── Species Description
│       │   ├── Taxonomy Information
│       │   └── Threats Assessment
│       ├── CITES Trade Data Tab
│       ├── Illegal Trade Tab
│       ├── Catch Data Tab
│       ├── Conservation Tab
│       └── References Tab
│
├── Research [/research]
│   ├── Research Tools Overview
│   ├── Species Comparison Tool [/research/species-comparison]
│   │   ├── Multi-species Selection Interface
│   │   ├── Interactive Visualization Dashboard
│   │   └── Export Functionality
│   ├── AI-Assisted Development [/research/ai-development]
│   │   ├── Development Methodology
│   │   ├── Technical Implementation
│   │   └── Vision Statement
│   ├── Data Export Tools (Coming Soon)
│   └── Publications Portal (Coming Soon)
│
├── Community [/community]
│   ├── Research Collaboration Section
│   ├── Local Communities Integration
│   └── Platform Development Notice
│
├── Glossary [/glossary]
│   ├── Alphabetical Navigation
│   ├── Category Filters
│   │   ├── Conservation (18 terms)
│   │   ├── Trade (32 terms)
│   │   ├── Taxonomy (9 terms)
│   │   ├── Data & Analysis (8 terms)
│   │   └── Geography (5 terms)
│   └── Search Functionality
│
└── About [/about]
    ├── Mission Statement
    ├── Platform Updates
    ├── Key Features
    ├── Team Information
    └── Technology Stack
```

## Technical Stack

### Frontend Architecture

#### Core Technologies
- **Framework**: React 18
- **Language**: TypeScript
- **Build Tool**: Vite
- **State Management**: TanStack Query (React Query)
- **Styling**: Tailwind CSS
- **Routing**: React Router

#### UI Components & Libraries
- Custom component library built with TypeScript
- Responsive design optimized for desktop and mobile
- Interactive data visualizations
- Image optimization with lazy loading

### Backend Infrastructure

#### Database & API
- **Platform**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth (context visible but not public-facing)
- **Data Access**: Row Level Security (RLS)
- **Edge Functions**: Serverless compute for data processing
- **Real-time**: WebSocket connections for live updates

#### Data Sources Integration
1. **CITES Trade Database** (v2025.1)
   - 489,148 legal trade records
   - 881 illegal seizure records
   - Coverage of 42 Arctic species

2. **IUCN Red List**
   - Conservation status assessments
   - Threat categorizations
   - Population trends

3. **NAMMCO** (North Atlantic Marine Mammal Commission)
   - Catch data for marine mammals
   - Regional conservation measures

4. **iNaturalist**
   - Species observations
   - Distribution data
   - Community science contributions

5. **CMS** (Convention on Migratory Species)
   - Migration patterns
   - International conservation agreements

### Deployment & Hosting
- **Hosting**: GitHub Pages (Static site hosting)
- **URL**: https://magnussmari.github.io/arctic-species-2025-frontend/
- **CI/CD**: GitHub Actions for automated deployment
- **Version Control**: Dual repository architecture
  - Frontend repository for React application
  - Backend repository for database schemas

## Key Features & Functionality

### 1. Species Browser
- **Gallery View**: Grid layout with species cards
- **Advanced Filtering**: Multi-criteria search and filtering
- **Pagination**: Configurable items per page (12, 24, 48, 96)
- **Species Cards**: Display scientific name, common name, and iNaturalist images

### 2. Species Detail Pages
Comprehensive species profiles including:
- Conservation status indicators (IUCN, CITES, CMS)
- Interactive data visualizations
- Trade data analysis
- Threat assessments
- Export to PDF functionality
- Multi-tab interface for organized information

### 3. Data Visualization Tools
- Time-series charts for trade data
- Conservation status timelines
- Geographic distribution maps
- Comparative analysis dashboards

### 4. Research Tools
- **Species Comparison Tool**: Multi-species trade data analysis
- **Data Export**: Structured data downloads for research
- **Advanced Search**: Complex query capabilities

### 5. Educational Resources
- **Comprehensive Glossary**: 72+ conservation terms
- **Interactive definitions**: Expandable explanations
- **Category-based browsing**: Organized by topic areas

## AI-Assisted Development Methodology

### Development Workflow
1. **Claude Code in VS Code**: Primary development environment
2. **Custom Supabase MCP Server**: Direct LLM-to-database connectivity
3. **Dual Repository Architecture**: Optimized for AI collaboration
4. **Scientific Literature Integration**: AI-powered research pipeline

### Key Innovations
- **Verification-First Development**: Continuous validation of features
- **Aligned Democratization**: Accessible to non-technical researchers
- **Legitimate Quality Assurance**: Transparent AI-assisted processes
- **Oversight Through Partnership**: Human-guided AI capabilities

## Current Metrics (As of August 2025)

- **Species Tracked**: 43 (with data for 140+ species in gallery)
- **CITES Trade Records**: 473,000+
- **Illegal Trade Seizures**: 919
- **Data Sources**: 6+ integrated platforms
- **Glossary Terms**: 72 definitions
- **Active Development**: Alpha v1.0

## Error Handling & Known Issues

### Current Technical Challenges
1. **Database Column Errors**: Some filter counts experiencing column specification issues
2. **404 Errors**: Occasional resource loading issues
3. **Authentication Context**: Present but not actively used in public interface

### Performance Considerations
- Lazy loading for images
- Pagination for large datasets
- Optimized database queries
- Client-side caching with TanStack Query

## Future Development Roadmap

### Planned Features
1. **Community Platform**: Collaboration tools for researchers
2. **Data Export Tools**: Advanced data extraction capabilities
3. **Publications Portal**: Research paper integration
4. **Enhanced Visualizations**: More interactive chart types
5. **Mobile Application**: Native mobile experience

### Technical Improvements
- Enhanced error handling
- Performance optimizations
- Expanded API capabilities
- Real-time collaboration features

## Significance for Conservation

The Arctic Tracker represents a paradigm shift in conservation technology:

1. **Democratized Access**: Makes complex conservation data accessible to all stakeholders
2. **Evidence-Based Decisions**: Provides comprehensive data for policy making
3. **Research Acceleration**: Enables rapid analysis of trade patterns
4. **Community Engagement**: Bridges scientific research and local knowledge
5. **Transparency**: Open access to critical conservation information

## Conclusion

The Arctic Tracker web application demonstrates how modern web technologies, combined with AI-assisted development, can create powerful tools for biodiversity conservation. By integrating multiple data sources into a unified, user-friendly platform, it empowers researchers, conservationists, and policymakers with the information needed to protect Arctic species effectively.

The application's architecture, built on React and Supabase, provides a scalable foundation for future enhancements while maintaining performance and accessibility. The innovative use of AI in development, while keeping AI out of user-facing functionality, ensures that the tool remains focused on serving conservation needs rather than technological complexity.

## Technical Specifications Summary

| Component | Technology |
|-----------|------------|
| Frontend Framework | React 18 with TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| State Management | TanStack Query |
| Backend | Supabase (PostgreSQL) |
| Hosting | GitHub Pages |
| Authentication | Supabase Auth (backend ready) |
| Data Sources | CITES, IUCN, NAMMCO, iNaturalist, CMS |
| Development Tools | Claude Code, Custom MCP Servers |
| Version | Alpha v1.0 |

## Contact Information

**Development Team:**
- Magnús Smári Smárason - AI-Project Manager and Lead Developer
- Tom Barry PhD - Research Scientist, Dean of School, UNAK

**Institution:** University of Akureyri, Iceland

**Repository:** https://github.com/magnussmari/arctic-species-2025-frontend/

---

*Document prepared for journal publication, August 2025*