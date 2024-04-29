# Notes
* Gui zum einfügen der mail-csv listen
* dynamisches definieren von csv attributen
* einstellbare schedulded task: different-ways-to-schedule-tasks-in-python-45e03d5411ee
* einstellbarer csv parser -> 
* jeden tag andere mail-liste.
    * 6 listen -> 1 sender

(2 python files)
# How to
* 1 ui file for defining lists....
    * import all csv-files
    * let user define columns for csv file
    * save data as json (file, + column definition for scheduling)
* After task is finished stop...
* 1 scheduled task file
    * create txt file where current file gets saved and by running the schedulded task, the file-number gets overwritten and set to new file(after every day)
    * if special day is reached. do not execute in cron (define in mail-sender python)
* log which mails got send

# Libaries
* Mail sending: https://github.com/Miksus/red-mail
* Cron Jobs: https://gaurav-adarshi.medium.com/different-ways-to-schedule-tasks-in-python-45e03d5411ee
* custom user inputs: https://stackoverflow.com/questions/56342198/python-code-to-read-csv-file-based-on-user-input
