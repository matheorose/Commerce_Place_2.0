import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-vercel-icon',
  standalone: true,
  templateUrl: './vercel-icon.component.html',
  styleUrls: ['./vercel-icon.component.css'],
})
export class VercelIconComponent {
  @Input() size = 17;
}
