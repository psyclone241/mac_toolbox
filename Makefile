# Helper script for setting up your apps local instance
# Contributors:
# Roy Keyes <keyes@ufl.edu>

help:
	@echo "Available tasks :"
	@echo "\tbackupstate - Check the state of my time machine backup drive"

taskname:
	@python backupstate.py
