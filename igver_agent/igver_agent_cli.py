#!/usr/bin/env python3
"""
🧬 IGVer Agent - User-Friendly Command Line Interface
A friendly, interactive CLI for genomic visualization and AI analysis
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import time

# Try to import rich for better terminal output
try:
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None
    rprint = print

# Import colorama for colored output (fallback if rich not available)
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main_igver_agent_fixed import GenomicAIAgent, AnalysisConfig
from test_config import get_singularity_image, TEST_BAMS

# Emoji icons for better UX
ICONS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'dna': '🧬',
    'robot': '🤖',
    'folder': '📁',
    'chart': '📊',
    'clock': '⏰',
    'search': '🔍',
    'screenshot': '📸',
    'report': '📄'
}

class UserFriendlyAgent:
    """User-friendly wrapper for IGVer Agent"""
    
    def __init__(self):
        self.agent = None
        self.config = None
        self.session_history = []
        self.load_user_preferences()
    
    def load_user_preferences(self):
        """Load user preferences from config file"""
        config_file = Path.home() / '.igver_agent_config.json'
        if config_file.exists():
            with open(config_file) as f:
                self.user_prefs = json.load(f)
        else:
            self.user_prefs = {
                'default_genome': 'hg38',
                'default_ai_provider': 'openai',
                'default_output_dir': str(Path.home() / 'igver_results'),
                'auto_open_report': True,
                'verbose': False
            }
    
    def save_user_preferences(self):
        """Save user preferences"""
        config_file = Path.home() / '.igver_agent_config.json'
        with open(config_file, 'w') as f:
            json.dump(self.user_prefs, f, indent=2)
    
    def print_welcome(self):
        """Print welcome message"""
        if RICH_AVAILABLE:
            console.print(Panel.fit(
                f"[bold cyan]{ICONS['dna']} IGVer Genomic AI Agent[/bold cyan]\n"
                "[dim]Automated IGV visualization with AI-powered analysis[/dim]",
                border_style="cyan"
            ))
        else:
            print("\n" + "=" * 60)
            print(f"{ICONS['dna']} IGVer Genomic AI Agent")
            print("Automated IGV visualization with AI-powered analysis")
            print("=" * 60)
    
    def print_status(self, message: str, status: str = 'info'):
        """Print status message with appropriate styling"""
        icon = ICONS.get(status, '')
        
        if RICH_AVAILABLE:
            if status == 'success':
                console.print(f"[green]{icon} {message}[/green]")
            elif status == 'error':
                console.print(f"[red]{icon} {message}[/red]")
            elif status == 'warning':
                console.print(f"[yellow]{icon} {message}[/yellow]")
            else:
                console.print(f"[blue]{icon} {message}[/blue]")
        elif COLORAMA_AVAILABLE:
            if status == 'success':
                print(f"{Fore.GREEN}{icon} {message}")
            elif status == 'error':
                print(f"{Fore.RED}{icon} {message}")
            elif status == 'warning':
                print(f"{Fore.YELLOW}{icon} {message}")
            else:
                print(f"{Fore.CYAN}{icon} {message}")
        else:
            print(f"{icon} {message}")
    
    def interactive_setup(self):
        """Interactive setup wizard for first-time users"""
        self.print_welcome()
        
        if RICH_AVAILABLE:
            console.print("\n[bold]Let's set up your analysis![/bold]\n")
        else:
            print("\nLet's set up your analysis!\n")
        
        # 1. Check API keys
        self.check_api_keys()
        
        # 2. Select genome
        genome = self.select_genome()
        
        # 3. Select AI provider
        ai_provider = self.select_ai_provider()
        
        # 4. Select output directory
        output_dir = self.select_output_directory()
        
        # 5. Configure analysis
        config = AnalysisConfig(
            genome=genome,
            output_format="png",
            remove_png=False
        )
        
        # 6. Initialize agent
        self.print_status("Initializing agent...", "info")
        
        try:
            self.agent = GenomicAIAgent(
                singularity_image=get_singularity_image(),
                output_base_dir=output_dir,
                config=config,
                ai_provider=ai_provider
            )
            self.print_status("Agent initialized successfully!", "success")
        except Exception as e:
            self.print_status(f"Failed to initialize agent: {e}", "error")
            self.suggest_fix(e)
            sys.exit(1)
        
        return self.agent
    
    def check_api_keys(self):
        """Check and help set up API keys"""
        openai_key = os.environ.get('OPENAI_API_KEY')
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        
        if not openai_key and not anthropic_key:
            self.print_status("No AI API keys found", "warning")
            
            if RICH_AVAILABLE:
                console.print("\nTo use AI analysis, you need an API key from:")
                console.print("  • OpenAI: https://platform.openai.com/api-keys")
                console.print("  • Anthropic: https://console.anthropic.com/")
                console.print("\nYou can:")
                console.print("  1. Set environment variable: export OPENAI_API_KEY=your-key")
                console.print("  2. Create .env file in igver_agent directory")
                console.print("  3. Use 'mock' provider for testing without API\n")
            else:
                print("\nNo API keys found. Using mock AI provider for testing.")
        else:
            if openai_key:
                self.print_status("OpenAI API key found", "success")
            if anthropic_key:
                self.print_status("Anthropic API key found", "success")
    
    def select_genome(self) -> str:
        """Interactive genome selection"""
        genomes = ['hg38', 'hg19', 'mm10', 'mm39']
        
        if RICH_AVAILABLE:
            genome = Prompt.ask(
                "\n[cyan]Select reference genome[/cyan]",
                choices=genomes,
                default=self.user_prefs['default_genome']
            )
        else:
            print("\nSelect reference genome:")
            for i, g in enumerate(genomes, 1):
                print(f"  {i}. {g}")
            choice = input(f"Choice [default: {self.user_prefs['default_genome']}]: ").strip()
            genome = choice if choice in genomes else self.user_prefs['default_genome']
        
        return genome
    
    def select_ai_provider(self) -> str:
        """Interactive AI provider selection"""
        providers = []
        
        if os.environ.get('OPENAI_API_KEY'):
            providers.append('openai')
        if os.environ.get('ANTHROPIC_API_KEY'):
            providers.append('anthropic')
        providers.append('mock')
        
        if len(providers) == 1:
            provider = providers[0]
            self.print_status(f"Using {provider} AI provider", "info")
        elif RICH_AVAILABLE:
            provider = Prompt.ask(
                "\n[cyan]Select AI provider[/cyan]",
                choices=providers,
                default=providers[0]
            )
        else:
            print("\nSelect AI provider:")
            for i, p in enumerate(providers, 1):
                print(f"  {i}. {p}")
            choice = input(f"Choice [default: {providers[0]}]: ").strip()
            provider = choice if choice in providers else providers[0]
        
        return provider
    
    def select_output_directory(self) -> str:
        """Interactive output directory selection"""
        default_dir = self.user_prefs['default_output_dir']
        
        if RICH_AVAILABLE:
            output_dir = Prompt.ask(
                f"\n[cyan]Output directory[/cyan]",
                default=default_dir
            )
        else:
            output_dir = input(f"Output directory [default: {default_dir}]: ").strip()
            if not output_dir:
                output_dir = default_dir
        
        # Create directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def select_bam_files(self) -> List[str]:
        """Interactive BAM file selection"""
        self.print_status("\nSelect BAM files:", "info")
        
        options = [
            "Enter BAM file paths",
            "Use test BAM files",
            "Load from file list",
            "Browse current directory"
        ]
        
        if RICH_AVAILABLE:
            choice = Prompt.ask(
                "[cyan]How would you like to provide BAM files?[/cyan]",
                choices=['1', '2', '3', '4'],
                default='1'
            )
        else:
            for i, opt in enumerate(options, 1):
                print(f"  {i}. {opt}")
            choice = input("Choice [1]: ").strip() or '1'
        
        if choice == '1':
            # Manual entry
            bam_files = []
            while True:
                path = input("BAM file path (or press Enter to finish): ").strip()
                if not path:
                    break
                if Path(path).exists():
                    bam_files.append(path)
                    self.print_status(f"Added: {path}", "success")
                else:
                    self.print_status(f"File not found: {path}", "error")
        
        elif choice == '2':
            # Test files
            bam_files = [str(p) for p in TEST_BAMS.values() if p.exists()]
            self.print_status(f"Using {len(bam_files)} test BAM files", "success")
        
        elif choice == '3':
            # Load from file
            list_file = input("Path to BAM list file: ").strip()
            bam_files = []
            with open(list_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if Path(line).exists():
                            bam_files.append(line)
        
        else:
            # Browse directory
            bam_files = list(Path.cwd().glob("*.bam"))
            bam_files = [str(f) for f in bam_files]
            
            if bam_files:
                print(f"Found {len(bam_files)} BAM files:")
                for f in bam_files[:5]:
                    print(f"  • {Path(f).name}")
                if len(bam_files) > 5:
                    print(f"  ... and {len(bam_files)-5} more")
            else:
                self.print_status("No BAM files found in current directory", "warning")
        
        return bam_files
    
    def select_regions(self) -> tuple:
        """Interactive region selection"""
        self.print_status("\nSelect genomic regions:", "info")
        
        options = [
            "Enter regions manually",
            "Load from file",
            "Use common cancer genes",
            "Use QC regions"
        ]
        
        if RICH_AVAILABLE:
            choice = Prompt.ask(
                "[cyan]How would you like to provide regions?[/cyan]",
                choices=['1', '2', '3', '4'],
                default='1'
            )
        else:
            for i, opt in enumerate(options, 1):
                print(f"  {i}. {opt}")
            choice = input("Choice [1]: ").strip() or '1'
        
        regions = []
        tags = []
        
        if choice == '1':
            # Manual entry
            while True:
                region = input("Region (chr:start-end) or press Enter to finish: ").strip()
                if not region:
                    break
                tag = input(f"Optional tag for {region}: ").strip()
                regions.append(region)
                tags.append(tag if tag else None)
                self.print_status(f"Added: {region} [{tag or 'no tag'}]", "success")
        
        elif choice == '2':
            # Load from file
            region_file = input("Path to regions file: ").strip()
            with open(region_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        regions.append(parts[0])
                        tags.append(parts[1] if len(parts) > 1 else None)
        
        elif choice == '3':
            # Common cancer genes
            regions = [
                "chr17:43044295-43045802",   # BRCA1
                "chr13:32315086-32400266",   # BRCA2
                "chr17:7571720-7579721",     # TP53
                "chr3:178936082-178938062"   # PIK3CA
            ]
            tags = ["BRCA1", "BRCA2", "TP53", "PIK3CA"]
            self.print_status(f"Using {len(regions)} cancer gene regions", "success")
        
        else:
            # QC regions
            regions = [
                "chr1:1000000-1010000",      # Standard region
                "chr19:58858172-58864865",   # High GC
                "chr4:1000000-1010000"       # Low GC
            ]
            tags = ["standard", "high_gc", "low_gc"]
            self.print_status(f"Using {len(regions)} QC regions", "success")
        
        return regions, tags
    
    def run_analysis_with_progress(self, bam_files: List[str], regions: List[str], 
                                  tags: List[str] = None, context: str = ""):
        """Run analysis with progress indicators"""
        
        session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Progress display
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                # Task 1: Generate screenshots
                task1 = progress.add_task(
                    f"{ICONS['screenshot']} Generating screenshots...", 
                    total=len(regions)
                )
                
                # Generate screenshots
                screenshots = self.agent.generate_screenshots(
                    bam_files=bam_files,
                    regions=regions,
                    region_tags=tags,
                    session_name=session_name
                )
                progress.update(task1, completed=len(regions))
                
                # Task 2: AI Analysis
                if screenshots and self.agent.ai_interpreter.provider != 'mock':
                    task2 = progress.add_task(
                        f"{ICONS['robot']} Running AI analysis...", 
                        total=len(screenshots)
                    )
                    
                    ai_analyses = self.agent.analyze_with_ai(screenshots, context)
                    progress.update(task2, completed=len(screenshots))
                else:
                    ai_analyses = {}
                
                # Task 3: Generate reports
                task3 = progress.add_task(
                    f"{ICONS['report']} Generating reports...", 
                    total=1
                )
                
                # Save results
                results = self.compile_results(
                    bam_files, regions, tags, screenshots, 
                    ai_analyses, session_name, context
                )
                progress.update(task3, completed=1)
        
        else:
            # Fallback progress display
            print(f"\n{ICONS['screenshot']} Generating screenshots...")
            screenshots = self.agent.generate_screenshots(
                bam_files=bam_files,
                regions=regions,
                region_tags=tags,
                session_name=session_name
            )
            
            if screenshots and self.agent.ai_interpreter.provider != 'mock':
                print(f"{ICONS['robot']} Running AI analysis...")
                ai_analyses = self.agent.analyze_with_ai(screenshots, context)
            else:
                ai_analyses = {}
            
            print(f"{ICONS['report']} Generating reports...")
            results = self.compile_results(
                bam_files, regions, tags, screenshots,
                ai_analyses, session_name, context
            )
        
        return results
    
    def compile_results(self, bam_files, regions, tags, screenshots, 
                       ai_analyses, session_name, context):
        """Compile and save results"""
        results = {
            'session_name': session_name,
            'timestamp': datetime.now().isoformat(),
            'input_summary': {
                'bam_files': bam_files,
                'regions': regions,
                'tags': tags,
                'context': context
            },
            'screenshots': screenshots,
            'ai_analyses': ai_analyses,
            'summary': {
                'total_regions': len(regions),
                'screenshots_generated': len(screenshots),
                'success_rate': f"{len(screenshots)/len(regions)*100:.1f}%" if regions else "0%"
            }
        }
        
        # Save results
        if self.agent:
            report_path = self.agent._save_results(results, session_name)
            html_path = self.agent._generate_html_report(results, session_name)
            results['report_path'] = report_path
            results['html_report'] = html_path
        
        return results
    
    def display_results(self, results: Dict):
        """Display results in a user-friendly way"""
        
        if RICH_AVAILABLE:
            # Create results table
            table = Table(title="Analysis Results", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Session", results['session_name'])
            table.add_row("Total Regions", str(results['summary']['total_regions']))
            table.add_row("Screenshots Generated", str(results['summary']['screenshots_generated']))
            table.add_row("Success Rate", results['summary']['success_rate'])
            
            if results.get('report_path'):
                table.add_row("JSON Report", Path(results['report_path']).name)
            if results.get('html_report'):
                table.add_row("HTML Report", Path(results['html_report']).name)
            
            console.print(table)
            
            # Show AI insights if available
            if results.get('ai_analyses'):
                console.print(f"\n[bold]{ICONS['robot']} AI Insights:[/bold]")
                for region, analysis in list(results['ai_analyses'].items())[:3]:
                    if 'error' not in analysis:
                        preview = analysis.get('analysis', '')[:200] + "..."
                        console.print(f"\n[cyan]{region}:[/cyan]")
                        console.print(f"[dim]{preview}[/dim]")
        
        else:
            # Simple text output
            print(f"\n{ICONS['chart']} Analysis Results")
            print("=" * 40)
            print(f"Session: {results['session_name']}")
            print(f"Total Regions: {results['summary']['total_regions']}")
            print(f"Screenshots: {results['summary']['screenshots_generated']}")
            print(f"Success Rate: {results['summary']['success_rate']}")
            
            if results.get('report_path'):
                print(f"JSON Report: {results['report_path']}")
            if results.get('html_report'):
                print(f"HTML Report: {results['html_report']}")
        
        # Offer to open HTML report
        if results.get('html_report') and self.user_prefs.get('auto_open_report'):
            self.open_report(results['html_report'])
    
    def open_report(self, html_path: str):
        """Open HTML report in browser"""
        import webbrowser
        
        try:
            if RICH_AVAILABLE:
                if Confirm.ask(f"\n{ICONS['folder']} Open HTML report in browser?"):
                    webbrowser.open(f"file://{Path(html_path).absolute()}")
            else:
                response = input(f"\n{ICONS['folder']} Open HTML report? (y/n): ")
                if response.lower() == 'y':
                    webbrowser.open(f"file://{Path(html_path).absolute()}")
        except Exception as e:
            self.print_status(f"Could not open report: {e}", "warning")
    
    def suggest_fix(self, error: Exception):
        """Suggest fixes for common errors"""
        error_str = str(error).lower()
        
        suggestions = []
        
        if 'singularity' in error_str:
            suggestions.append("Install Singularity: sudo apt-get install singularity-container")
            suggestions.append("Or use Docker: export IGVER_NO_SINGULARITY=1")
        
        if 'bam' in error_str and 'not found' in error_str:
            suggestions.append("Check BAM file paths are correct")
            suggestions.append("Ensure BAM index files (.bai) exist")
        
        if 'api' in error_str or 'openai' in error_str:
            suggestions.append("Check your API key: echo $OPENAI_API_KEY")
            suggestions.append("Or use mock provider for testing")
        
        if 'permission' in error_str:
            suggestions.append("Check file permissions")
            suggestions.append("Try running with appropriate permissions")
        
        if suggestions:
            self.print_status("\nSuggested fixes:", "info")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
    
    def run_interactive(self):
        """Run the full interactive workflow"""
        try:
            # Setup
            self.interactive_setup()
            
            # Get inputs
            bam_files = self.select_bam_files()
            if not bam_files:
                self.print_status("No BAM files selected", "error")
                return
            
            regions, tags = self.select_regions()
            if not regions:
                self.print_status("No regions selected", "error")
                return
            
            # Get context
            if RICH_AVAILABLE:
                context = Prompt.ask(
                    f"\n[cyan]{ICONS['info']} Analysis context (optional)[/cyan]",
                    default=""
                )
            else:
                context = input(f"\n{ICONS['info']} Analysis context (optional): ").strip()
            
            # Run analysis
            results = self.run_analysis_with_progress(bam_files, regions, tags, context)
            
            # Display results
            self.display_results(results)
            
            # Save preferences
            if RICH_AVAILABLE:
                if Confirm.ask("\nSave preferences for next time?"):
                    self.save_user_preferences()
            
            self.print_status("\nAnalysis complete!", "success")
            
        except KeyboardInterrupt:
            self.print_status("\nAnalysis cancelled by user", "warning")
        except Exception as e:
            self.print_status(f"\nError: {e}", "error")
            self.suggest_fix(e)
            sys.exit(1)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='IGVer Genomic AI Agent - User-Friendly Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended for new users)
  %(prog)s --interactive
  
  # Quick analysis with defaults
  %(prog)s -b sample.bam -r "chr1:1000-2000"
  
  # Multiple BAMs and regions
  %(prog)s -b tumor.bam normal.bam -r regions.txt
  
  # With AI analysis
  %(prog)s -b sample.bam -r "chr17:43044295-43045802" --ai openai --context "BRCA1 screening"
  
  # Batch mode with file inputs
  %(prog)s -b bam_list.txt -r regions.bed --output results/ --genome hg38
        """
    )
    
    # Input arguments
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Run in interactive mode (recommended)')
    parser.add_argument('-b', '--bam', nargs='+', dest='bam_files',
                       help='BAM file(s) or file with BAM list')
    parser.add_argument('-r', '--regions', nargs='+',
                       help='Genomic regions or region file')
    
    # Configuration
    parser.add_argument('-g', '--genome', default='hg38',
                       choices=['hg19', 'hg38', 'mm10', 'mm39'],
                       help='Reference genome')
    parser.add_argument('-o', '--output', default='igver_results',
                       help='Output directory')
    parser.add_argument('--ai', choices=['openai', 'anthropic', 'mock'],
                       default='mock', help='AI provider')
    parser.add_argument('--context', default='',
                       help='Context for AI analysis')
    
    # Options
    parser.add_argument('--no-ai', action='store_true',
                       help='Skip AI analysis')
    parser.add_argument('--no-report', action='store_true',
                       help='Skip HTML report generation')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Create agent wrapper
    agent_cli = UserFriendlyAgent()
    
    if args.interactive or (not args.bam_files and not args.regions):
        # Run interactive mode
        agent_cli.run_interactive()
    else:
        # Run with command-line arguments
        if not args.bam_files or not args.regions:
            parser.error("Both --bam and --regions are required in non-interactive mode")
        
        # Initialize agent
        config = AnalysisConfig(
            genome=args.genome,
            output_format='png',
            remove_png=False
        )
        
        agent_cli.agent = GenomicAIAgent(
            singularity_image=get_singularity_image(),
            output_base_dir=args.output,
            config=config,
            ai_provider=args.ai if not args.no_ai else 'mock'
        )
        
        # Process inputs
        bam_files = []
        for bam in args.bam_files:
            if Path(bam).suffix == '.txt':
                with open(bam) as f:
                    bam_files.extend([line.strip() for line in f if line.strip()])
            else:
                bam_files.append(bam)
        
        regions = []
        for region in args.regions:
            if Path(region).exists():
                with open(region) as f:
                    regions.extend([line.strip().split()[0] for line in f if line.strip()])
            else:
                regions.append(region)
        
        # Run analysis
        agent_cli.print_welcome()
        results = agent_cli.run_analysis_with_progress(
            bam_files=bam_files,
            regions=regions,
            context=args.context
        )
        agent_cli.display_results(results)

if __name__ == "__main__":
    main()