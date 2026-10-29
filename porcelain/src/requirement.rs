//! Which `pub` a project needs, and saying so before anything runs.
//!
//! A project states the releases of `pub` it works with, as a version
//! requirement in the forms `publet_algorithms::version::satisfies` reads
//! (`0.2.2+`, `^0.2`, `0.2`):
//!
//! - in a workspace, as a `pub=` line in `.publet/config`, beside
//!   `author=` and `policy=`;
//! - anywhere else, such as a repository whose scripts call `pub`, as the
//!   first line of a `pub-version.txt` (blank lines are skipped, and `#`
//!   starts a comment, on a line of its own or after the requirement).
//!
//! Before any command but `--version`, `version`, `help` (`-h`, `--help`)
//! and `require`, `pub` looks for either in the current directory and then
//! each parent, nearest first, as git finds `.git`, and stops with exit 2
//! and the release to install when this build does not meet it, or when
//! what it finds is not a requirement. Nothing is fetched: the check is
//! between the build and a file the project keeps. `PUB_IGNORE_VERSION=1`
//! skips it, to try another release on purpose.
//!
//! The files are another party's input once a repository is cloned, so only
//! regular files are read (never a FIFO or a device, which could block), at
//! most [`LIMIT`] bytes of them, and a requirement is accepted only in the
//! forms above: anything else is refused by name, quoted with escapes, so a
//! file cannot write control characters to the terminal.

use std::path::{Path, PathBuf};

use publet_algorithms::version::satisfies;

use crate::workspace::DIR;

/// The file a project without a workspace states its requirement in.
pub(crate) const FILE: &str = "pub-version.txt";

/// The environment variable that skips the check.
pub(crate) const IGNORE: &str = "PUB_IGNORE_VERSION";

const REPOSITORY: &str = "https://github.com/schryer/publet";

/// The most of a declaring file read: a requirement is one short line.
pub(crate) const LIMIT: u64 = 4096;

/// This build's version.
pub(crate) fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// A declaration found: the requirement as written, the file stating it.
pub(crate) type Declared = (String, PathBuf);

/// The text of `path` if it is a regular file (a symlink to one is
/// followed); `Ok(None)` when there is no such file or it is something else.
fn read_regular(path: &Path) -> Result<Option<String>, String> {
    use std::io::Read as _;
    match std::fs::metadata(path) {
        Ok(m) if m.is_file() => {}
        _ => return Ok(None),
    }
    let mut bytes = Vec::new();
    std::fs::File::open(path)
        .and_then(|f| f.take(LIMIT).read_to_end(&mut bytes))
        .map_err(|e| format!("{}: {e}", path.display()))?;
    let text = String::from_utf8(bytes).map_err(|_| {
        format!(
            "{}: not UTF-8 text, so no requirement can be read from it",
            path.display()
        )
    })?;
    Ok(Some(text.trim_start_matches('\u{feff}').to_owned()))
}

/// A line with its comment and surrounding space removed.
fn uncommented(line: &str) -> &str {
    line.split('#').next().unwrap_or("").trim()
}

/// The nearest requirement stated at or above `start`, and the file stating it.
///
/// # Errors
///
/// Returns a message when the nearest declaring file cannot be read as text.
pub(crate) fn declared(start: &Path) -> Result<Option<Declared>, String> {
    for dir in start.ancestors() {
        let config = dir.join(DIR).join("config");
        if let Some(text) = read_regular(&config)?
            && let Some(req) = text
                .lines()
                .find_map(|l| l.strip_prefix("pub="))
                .map(uncommented)
                .filter(|r| !r.is_empty())
        {
            return Ok(Some((req.to_owned(), config)));
        }
        let file = dir.join(FILE);
        if let Some(text) = read_regular(&file)?
            && let Some(req) = text.lines().map(uncommented).find(|l| !l.is_empty())
        {
            return Ok(Some((req.to_owned(), file)));
        }
    }
    Ok(None)
}

/// Whether `requirement` has a form `satisfies` reads: `X.Y.Z+`, `^X.Y`, or
/// a version prefix such as `0.2`, of dot-separated numbers.
pub(crate) fn well_formed(requirement: &str) -> bool {
    let core = requirement
        .strip_prefix('^')
        .or_else(|| requirement.strip_suffix('+'))
        .unwrap_or(requirement);
    !core.is_empty()
        && core
            .split('.')
            .all(|p| !p.is_empty() && p.bytes().all(|b| b.is_ascii_digit()))
}

/// Whether this build meets `requirement`, stated by `source`; if not, what
/// to tell the person running it.
///
/// # Errors
///
/// Returns the message to print when this build does not meet it.
pub(crate) fn check(requirement: &str, source: &str) -> Result<(), String> {
    if !well_formed(requirement) {
        return Err(format!(
            "{source} states {requirement:?}, which is not a version requirement: \
             write one such as 0.2.2+ (that release or later), ^0.2 or 0.2.\n\
             Set {IGNORE}=1 to run this pub anyway."
        ));
    }
    if satisfies(version(), requirement) {
        return Ok(());
    }
    Err(format!(
        "this project needs pub {requirement} (from {source}); this is pub {}.\n\
         Install a release that meets it:\n  {}\n\
         or set {IGNORE}=1 to run this one anyway.",
        version(),
        install_line(requirement),
    ))
}

/// The command installing a release that meets `requirement`: its lowest
/// release when the requirement names one, otherwise a tag to choose.
pub(crate) fn install_line(requirement: &str) -> String {
    let lowest = requirement
        .trim_start_matches('^')
        .trim_end_matches('+')
        .to_owned();
    let tag =
        if lowest.split('.').count() == 3 && lowest.split('.').all(|p| p.parse::<u64>().is_ok()) {
            format!("v{lowest}")
        } else {
            "<release tag>".to_owned()
        };
    format!("cargo install --locked --git {REPOSITORY} --tag {tag} publet-cli pub-store")
}

/// Check the requirement declared at or above the current directory, unless
/// `PUB_IGNORE_VERSION=1`.
///
/// # Errors
///
/// Returns the message to print when this build does not meet it.
pub(crate) fn enforce() -> Result<(), String> {
    if std::env::var(IGNORE).is_ok_and(|v| v == "1") {
        return Ok(());
    }
    let Ok(here) = std::env::current_dir() else {
        return Ok(());
    };
    match declared(&here)? {
        Some((req, source)) => check(&req, &source.display().to_string()),
        None => Ok(()),
    }
}

/// `pub require [REQUIREMENT]`: whether this build meets `REQUIREMENT`, or
/// with none, the requirement declared here. Prints nothing when it does.
///
/// # Errors
///
/// Returns the message to print when it does not, or when no requirement is
/// given or declared.
pub(crate) fn run(args: &[String]) -> Result<(), String> {
    match args {
        [] => {
            let here = std::env::current_dir().map_err(|e| e.to_string())?;
            let (req, source) = declared(&here)?.ok_or(format!(
                "no requirement given, and none declared here: give one (pub require 0.2.2+), \
                 or state it in {FILE} or as pub= in {DIR}/config"
            ))?;
            check(&req, &source.display().to_string())
        }
        [req] => check(req, "the command line"),
        _ => Err("usage: pub require [REQUIREMENT], such as 0.2.2+ or ^0.2".to_owned()),
    }
}

/// What to say for a command this build does not have: it may be newer.
pub(crate) fn unknown_command(command: &str) -> String {
    format!(
        "unknown command: {command}\n\
         This is pub {}. If {command} is a command of a newer release, install it:\n  {}\n\
         (`pub help` lists this release's commands.)",
        version(),
        install_line("<release tag>"),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_nearest_declaration_wins_and_a_workspace_beats_a_file_beside_it() {
        let root = std::env::temp_dir().join(format!("pub-req-{}", std::process::id()));
        let inner = root.join("a").join("b");
        std::fs::create_dir_all(inner.join(DIR)).unwrap();
        std::fs::write(
            root.join(FILE),
            "\u{feff}# pub for these scripts\n\n0.2.2+  # pinned\n",
        )
        .unwrap();
        assert_eq!(declared(&inner).unwrap().unwrap().0, "0.2.2+");
        std::fs::write(inner.join(DIR).join("config"), "author=x\npub=^0.3\n").unwrap();
        std::fs::write(inner.join(FILE), "0.1+\n").unwrap();
        let (req, source) = declared(&inner).unwrap().unwrap();
        assert_eq!(req, "^0.3");
        assert!(source.ends_with("config"));
        std::fs::remove_dir_all(&root).unwrap();
    }

    #[test]
    fn a_requirement_not_met_names_the_release_to_install() {
        assert!(check("0.0.1+", "x").is_ok());
        let message = check("999.0.0+", "pub-version.txt").unwrap_err();
        assert!(
            message.contains("needs pub 999.0.0+ (from pub-version.txt)"),
            "{message}"
        );
        assert!(message.contains("--tag v999.0.0"), "{message}");
        assert!(install_line("^0.2").contains("<release tag>"));
    }

    #[test]
    fn only_requirements_are_accepted_and_others_are_quoted() {
        for good in ["0.2.2+", "^0.2", "0.2", "1"] {
            assert!(well_formed(good), "{good}");
        }
        for bad in ["latest", "", "+", "^", "0..2", "0.2.x", "\u{1b}[31m0.2"] {
            assert!(!well_formed(bad), "{bad:?}");
        }
        let message = check("\u{1b}[31mlatest", "pub-version.txt").unwrap_err();
        assert!(message.contains("\\u{1b}"), "{message}");
        assert!(!message.contains('\u{1b}'), "{message}");
    }

    #[cfg(unix)]
    #[test]
    fn a_fifo_or_an_oversized_file_never_blocks_the_check() {
        let root = std::env::temp_dir().join(format!("pub-req-fifo-{}", std::process::id()));
        std::fs::create_dir_all(&root).unwrap();
        let made = std::process::Command::new("mkfifo")
            .arg(root.join(FILE))
            .status();
        if made.is_ok_and(|s| s.success()) {
            assert!(declared(&root).unwrap().is_none());
            std::fs::remove_file(root.join(FILE)).unwrap();
        }
        std::fs::write(root.join(FILE), format!("{}\n0.1+\n", "#".repeat(10_000))).unwrap();
        assert!(declared(&root).unwrap().is_none());
        std::fs::remove_dir_all(&root).unwrap();
    }
}
