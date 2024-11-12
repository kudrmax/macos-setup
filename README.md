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

3. Clone this repo
   - Clone this repo to some directory.
   - Manually copy all files including hidden files to `~` (you can't do it automaticly because MacOS permisions).
   - Check that `git status` is working from `~` and is up to date.

> [!WARNING]
> If you're NOT me, be carfull with file `.gitconfig`. If you just copy the file, you will create commits in git with MY author name!

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
brew install powerlevel10k
```

Replace configs for Oh-My-Zsh and p10k:

```
cd
git restore ~/.zshrc
git restore ~/.p10k.zsh
source ~/.zshrc
clear
```

Configure p10k (if needed):

```
p10k configure
```

5. Install itrem2

```
brew install --cask iterm2
```

6. Instal lazygit:

```
brew install lazygit
brew install git-delta # for pretty git diff
```

7. Install lazydocker

```
brew install lazydocker
```

Import settings to iterm2:

Settings -> General -> Settings -> Import All Settings and Data... -> `~/.config/iTerm2 State.itermexport`

## Apps

```
brew install --cask google-chrome
brew install --cask telegram
brew install --cask iina
brew install --cask todoist
brew install --cask obsidian
brew install --cask morgen
brew install --cask yandex-music
```

## Утилиты:

### Разные утилиты

```
brew install --cask bitwarden
brew install --cask appcleaner
brew install --cask bettertouchtool
brew install --cask karabiner-elements
brew install --cask sublime-text
```

- [xnip](https://xnipapp.com/)
- [OwlOCR](https://www.owlocr.com/)

### Chrome extentions

- [bitwarden](https://chromewebstore.google.com/detail/bitwarden-password-manage/nngceckbapebfimnlniiiahkandclblb)
- [video-speed-controller](https://chromewebstore.google.com/detail/video-speed-controller/nffaoalbilbmmfgbnbgppjihopabppdk)
- [addblock](https://chromewebstore.google.com/detail/adblock-%E2%80%94-block-ads-acros/gighmmpiobklfepjocnamgkkbiglidom)
- [sponsorblock](https://chromewebstore.google.com/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone?hl=en)
- [omnivore](https://chromewebstore.google.com/detail/omnivore/blkggjdmcfjdbmmmlfcpplkchpeaiiab)

### BTT

```
brew install --cask bettertouchtool
```

Импортировать настройки:
1. Presets -> Import presets -> `~/.config/btt_preset.bttpreset`
2. Preset (in left top corner) -> delete default preset
3. Fix 4 Finger Swipe Down: 4 Finger Swipe Down -> Application Switcher -> Use Gesture Mode

### Karabiner-Elements

```
brew install --cask karabiner-elements
```

If you have problems with `karabiner_graber`, restart the computer.

## To do

Найти альтернативу или купить (пока только взлом, то есть не могу поставить на корпоративный ноут):
- Bartender 5
- Alfred 5
- CleanMyMac X
- Middle
