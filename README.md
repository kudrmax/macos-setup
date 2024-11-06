# MacOS setup

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

4. Install Oh-My-Zsh: [link](https://ohmyz.sh/)

```
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

4. Install plugins:

```
brew install zsh-autosuggestions
brew install zsh-syntax-highlighting
brew install zsh-you-should-use
```

4. Install p10k: [link](https://github.com/romkatv/powerlevel10k)

```
brew install zsh-powerlevel10k
```

5. Replace configs

```
git restore ~/.zshrc
git restore ~/.p10k.zsh
source ~/.zshrc
```

5. Configure p10k (if needed):

```
p10k configure
```

6. Instal lazygit:

```
brew install lazygit
brew install git-delta
```

2. Install itrem2: [link](https://iterm2.com/downloads.html)

```
brew install --cask iterm2
```

6. Configure iterm2:

ДОПИСАТЬ

## BitWarden

Install: [extention](https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb) and [app](https://bitwarden.com/download/)

## AppCleaner

```
brew install --cask appcleaner
```

## BTT

```
brew install --cask bettertouchtool
```

- Configure:

## Karabiner

- Install Karabiner-Elements:
- Configure:

## Obsidian

```
brew install --cask obsidian
```

Configure:

```
git clone ...
```
