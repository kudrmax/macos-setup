# MacOS setup

## Extentions

- [bitwarden](https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb)
- [video-speed-controller](https://chromewebstore.google.com/detail/video-speed-controller/nffaoalbilbmmfgbnbgppjihopabppdk)
- [addblock](https://chromewebstore.google.com/detail/adblock-%E2%80%94-block-ads-acros/gighmmpiobklfepjocnamgkkbiglidom)
- [sponsorblock](https://chromewebstore.google.com/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone?hl=en)
- [omnivore](https://chromewebstore.google.com/detail/omnivore/blkggjdmcfjdbmmmlfcpplkchpeaiiab)

## Apps

```
brew install --cask bitwarden
brew install --cask appcleaner
brew install --cask obsidian
brew install --cask bettertouchtool
```

## Terminal

1. Install brew: [link](https://brew.sh/)

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Install micro:

```
brew install micro
```

2. Clone this repo to `~`

4. Oh-My-Zsh and p10k

Install Oh-My-Zsh:

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

Install plugins for zsh:

```
brew install zsh-autosuggestions
brew install zsh-syntax-highlighting
brew install zsh-you-should-use
```

Install p10k theme: [link](https://github.com/romkatv/powerlevel10k)

```
brew install zsh-powerlevel10k
```

Replace configs for Oh-My-Zsh and p10k:

```
git restore ~/.zshrc
git restore ~/.p10k.zsh
source ~/.zshrc
```

Configure p10k (if needed):

```
p10k configure
```

2. Install itrem2: [link](https://iterm2.com/downloads.html)

```
brew install --cask iterm2
```

6. Instal lazygit:

```
brew install lazygit
brew install git-delta
```

1. Install lazydocker

```
brew install lazydocker
```

Import settings to iterm2:

Settings -> General -> Settings -> Import All Settings and Data... -> `~/.config/iTerm2 State.itermexport`


