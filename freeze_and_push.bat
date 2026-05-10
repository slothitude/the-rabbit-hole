@echo off
cd /d C:\Users\aaron\Desktop\dev\the-rabbit-hole
C:\Python313\python.exe freeze.py && (
    cd _site
    if exist .git rd /s /q .git
    git init
    git add -A
    git commit -m "Auto snapshot %date:~10,4%-%date:~4,2%-%date:~7,2% %time:~0,2%%time:~3,2%"
    git branch -M gh-pages
    git remote add origin https://github.com/slothitude/the-rabbit-hole.git
    git push -f origin gh-pages
    cd ..
    echo [%date% %time%] Freeze+push succeeded >> freeze.log
) || (
    echo [%date% %time%] Freeze failed >> freeze.log
)
