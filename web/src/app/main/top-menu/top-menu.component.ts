import { Component, Input, OnInit } from '@angular/core';

export interface MenuItem {
  link: string;
  label: string;
}

@Component({
  selector: 'app-top-menu',
  templateUrl: './top-menu.component.html',
  styleUrls: ['./top-menu.component.scss']
})
export class TopMenuComponent implements OnInit {

  @Input() items: MenuItem[] = [];

  constructor() { }

  ngOnInit(): void {
  }

}
